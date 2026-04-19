from abc import ABC, abstractmethod
from datetime import datetime


# ===================== TRANSACOES =====================

class Transacao(ABC):
    @abstractmethod
    def registrar(self, conta):
        pass


class Deposito(Transacao):
    def __init__(self, valor: float):
        self.valor = valor

    def registrar(self, conta):
        sucesso = conta.depositar(self.valor)
        if sucesso:
            conta.historico.adicionar_transacao(self)


class Saque(Transacao):
    def __init__(self, valor: float):
        self.valor = valor

    def registrar(self, conta):
        sucesso = conta.sacar(self.valor)
        if sucesso:
            conta.historico.adicionar_transacao(self)


# ===================== HISTORICO =====================

class Historico:
    def __init__(self):
        self.transacoes = []

    def adicionar_transacao(self, transacao):
        self.transacoes.append({
            "tipo": transacao.__class__.__name__,
            "valor": transacao.valor,
            "data": datetime.now()
        })


# ===================== CONTA =====================

class Conta:
    def __init__(self, numero, cliente):
        self.saldo = 0.0
        self.numero = numero
        self.agencia = "0001"
        self.cliente = cliente
        self.historico = Historico()

    @classmethod
    def nova_conta(cls, cliente, numero):
        return cls(numero, cliente)

    def sacar(self, valor):
        if valor > self.saldo:
            print("Saldo insuficiente.")
            return False

        if valor <= 0:
            print("Valor inválido.")
            return False

        self.saldo -= valor
        return True

    def depositar(self, valor):
        if valor <= 0:
            print("Valor inválido.")
            return False

        self.saldo += valor
        return True


# ===================== CONTA CORRENTE =====================

class ContaCorrente(Conta):
    def __init__(self, numero, cliente, limite=500, limite_saques=3):
        super().__init__(numero, cliente)
        self.limite = limite
        self.limite_saques = limite_saques

    def sacar(self, valor):
        numero_saques = sum(
            1 for t in self.historico.transacoes if t["tipo"] == "Saque"
        )

        if valor > self.limite:
            print("Valor excede o limite.")
            return False

        if numero_saques >= self.limite_saques:
            print("Limite de saques atingido.")
            return False

        return super().sacar(valor)


# ===================== CLIENTE =====================

class Cliente:
    def __init__(self, endereco):
        self.endereco = endereco
        self.contas = []

    def realizar_transacao(self, conta, transacao):
        transacao.registrar(conta)

    def adicionar_conta(self, conta):
        self.contas.append(conta)


# ===================== PESSOA FISICA =====================

class PessoaFisica(Cliente):
    def __init__(self, nome, cpf, data_nascimento, endereco):
        super().__init__(endereco)
        self.nome = nome
        self.cpf = cpf
        self.data_nascimento = data_nascimento


# ===================== TESTE =====================

if __name__ == "__main__":
    cliente = PessoaFisica(
        nome="Eduardo",
        cpf="12345678900",
        data_nascimento="01-01-2000",
        endereco="Manaus"
    )

    conta = ContaCorrente.nova_conta(cliente, numero=1)
    cliente.adicionar_conta(conta)

    d1 = Deposito(1000)
    cliente.realizar_transacao(conta, d1)

    s1 = Saque(200)
    cliente.realizar_transacao(conta, s1)

    print("Saldo:", conta.saldo)
    print("Histórico:", conta.historico.transacoes)