from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Field, Relationship, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from jose import jwt, JWTError

# ===================== CONFIG =====================

DATABASE_URL = "postgresql+asyncpg://postgres:senha@localhost:5432/banco_api"
SECRET_KEY = "secret"
ALGORITHM = "HS256"

app = FastAPI(title="Banco API Completo")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ===================== DATABASE =====================

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session():
    async with async_session() as session:
        yield session

# ===================== MODELS =====================

class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cpf: str
    senha: str

    contas: List["Conta"] = Relationship(back_populates="cliente")


class Conta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    numero: int
    saldo: float = 0

    cliente_id: int = Field(foreign_key="cliente.id")
    cliente: Optional[Cliente] = Relationship(back_populates="contas")

    transacoes: List["Transacao"] = Relationship(back_populates="conta")


class Transacao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str
    valor: float
    data: datetime = Field(default_factory=datetime.utcnow)

    conta_id: int = Field(foreign_key="conta.id")
    conta: Optional[Conta] = Relationship(back_populates="transacoes")

# ===================== INIT DB =====================

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# ===================== SCHEMAS =====================

class ClienteCreate(BaseModel):
    nome: str
    cpf: str
    senha: str


class TransacaoSchema(BaseModel):
    valor: float

# ===================== JWT =====================

def criar_token(user_id: int):
    return jwt.encode({"sub": str(user_id)}, SECRET_KEY, algorithm=ALGORITHM)


async def get_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(401, "Token inválido")

    result = await session.execute(select(Cliente).where(Cliente.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    return user

# ===================== ROTAS =====================

@app.post("/clientes")
async def criar_cliente(
    dados: ClienteCreate,
    session: AsyncSession = Depends(get_session)
):
    cliente = Cliente(**dados.dict())

    session.add(cliente)
    await session.commit()
    await session.refresh(cliente)

    return cliente


@app.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Cliente).where(Cliente.cpf == form.username)
    )
    cliente = result.scalar_one_or_none()

    if not cliente or cliente.senha != form.password:
        raise HTTPException(401, "Credenciais inválidas")

    token = criar_token(cliente.id)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/contas")
async def criar_conta(
    user: Cliente = Depends(get_user),
    session: AsyncSession = Depends(get_session)
):
    conta = Conta(numero=user.id * 1000 + 1, cliente_id=user.id)

    session.add(conta)
    await session.commit()
    await session.refresh(conta)

    return conta


@app.post("/contas/{id}/deposito")
async def depositar(
    id: int,
    dados: TransacaoSchema,
    user: Cliente = Depends(get_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Conta).where(Conta.id == id))
    conta = result.scalar_one_or_none()

    if not conta or conta.cliente_id != user.id:
        raise HTTPException(404, "Conta não encontrada")

    if dados.valor <= 0:
        raise HTTPException(400, "Valor inválido")

    conta.saldo += dados.valor

    transacao = Transacao(
        tipo="Deposito",
        valor=dados.valor,
        conta_id=conta.id
    )

    session.add(transacao)
    await session.commit()

    return {"saldo": conta.saldo}


@app.post("/contas/{id}/saque")
async def sacar(
    id: int,
    dados: TransacaoSchema,
    user: Cliente = Depends(get_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Conta).where(Conta.id == id))
    conta = result.scalar_one_or_none()

    if not conta or conta.cliente_id != user.id:
        raise HTTPException(404, "Conta não encontrada")

    if dados.valor <= 0 or dados.valor > conta.saldo:
        raise HTTPException(400, "Saque inválido")

    conta.saldo -= dados.valor

    transacao = Transacao(
        tipo="Saque",
        valor=dados.valor,
        conta_id=conta.id
    )

    session.add(transacao)
    await session.commit()

    return {"saldo": conta.saldo}


@app.get("/contas/{id}")
async def ver_conta(
    id: int,
    user: Cliente = Depends(get_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Conta).where(Conta.id == id))
    conta = result.scalar_one_or_none()

    if not conta or conta.cliente_id != user.id:
        raise HTTPException(404, "Conta não encontrada")

    result = await session.execute(
        select(Transacao).where(Transacao.conta_id == conta.id)
    )
    transacoes = result.scalars().all()

    return {
        "saldo": conta.saldo,
        "transacoes": transacoes
    }