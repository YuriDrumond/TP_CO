import re
import sys
import os

# ═══════════════════════════════════════════════════════════════════
#  LÉXICO
# ═══════════════════════════════════════════════════════════════════

KEYWORDS = {
    "if", "else", "while", "for", "do",
    "return", "int", "float", "double",
    "char", "void", "struct",
}

TOKEN_RULES = [

    ("COMENTARIO",     r"/\*[\s\S]*?\*/|//[^\n]*"),

    ("PREPROCESSADOR", r"#(?:include|define)\b"),

    ("HEADER_SISTEMA", r"<[A-Za-z0-9_./]+>"),

    ("HEADER_ARQUIVO", r'"[A-Za-z0-9_./\\-]+"'),

    ("STRING",         r'"(?:[^"\\]|\\.)*"'),

    ("CHAR",           r"'(?:[^'\\]|\\.)'"),

    ("NUMERO_REAL",    r"(?<!\w)[0-9]*\.[0-9]+(?!\w)"),

    ("NUMERO_INT",     r"(?<!\w)[0-9]+(?!\w)"),

    ("LOGICA",         r"==|!=|<=|>=|&&|\|\||[!<>]"),

    ("OPERADOR",       r"\+\+|--|[+\-*/&]"),

    ("ATRIBUICAO",     r"=(?!=)"),

    ("DELIMITADOR",    r"[(){}\[\]]"),

    ("PONTUACAO",      r"[;,:\.]"),

    ("IDENTIFICADOR",  r"\b[A-Za-z_][A-Za-z0-9_]*\b"),

    ("ESPACO",         r"\s+"),

    ("ERRO",           r"."),
]

MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{nome}>{regex})" for nome, regex in TOKEN_RULES),
    re.DOTALL,
)


# ═══════════════════════════════════════════════════════════════════
#  LÉXICO
# ═══════════════════════════════════════════════════════════════════

def analisar(codigo: str) -> list[tuple[str, str, int, int]]:

    tokens = []

    for m in MASTER_PATTERN.finditer(codigo):

        tipo  = m.lastgroup
        valor = m.group()
        pos   = m.start()

        linha = codigo.count("\n", 0, pos) + 1

        ultimo_nl = codigo.rfind("\n", 0, pos)
        coluna = pos - ultimo_nl

        if tipo in {"ESPACO", "COMENTARIO"}:
            continue

        if tipo == "IDENTIFICADOR" and valor in KEYWORDS:
            tipo = "PALAVRA_CHAVE"

        tokens.append((valor, tipo, linha, coluna))

    return tokens


def gerar_saida(tokens):

    linhas = []

    for valor, tipo, linha, coluna in tokens:
        linhas.append(f"{valor}\t{tipo}\t{linha}\t{coluna}")

    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════
#  SINTÁTICO
# ═══════════════════════════════════════════════════════════════════

TIPOS_BASICOS = {
    "int",
    "float",
    "double",
    "char",
    "void"
}


class ErroSintatico(Exception):
    pass


class Parser:

    def __init__(self, tokens):

        self.tokens = tokens
        self.pos = 0
        self.erros = []

    # ──────────────────────────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────────────────────────

    def atual(self):

        if self.pos < len(self.tokens):
            return self.tokens[self.pos]

        return ("EOF", "EOF", -1, -1)

    def valor(self):
        return self.atual()[0]

    def tipo(self):
        return self.atual()[1]

    def info(self):

        tok = self.atual()

        return f"linha {tok[2]}, coluna {tok[3]}"

    def proximo(self, offset=1):

        idx = self.pos + offset

        if idx < len(self.tokens):
            return self.tokens[idx]

        return ("EOF", "EOF", -1, -1)

    def vv(self, *valores):
        return self.valor() in valores

    def tt(self, *tipos):
        return self.tipo() in tipos

    def eh_tipo(self):

        if self.valor() == "struct":
            return True

        return (
            self.tt("PALAVRA_CHAVE")
            and self.valor() in TIPOS_BASICOS
        )

    def consumir(self, valor_esp=None, tipo_esp=None):

        tok = self.atual()

        if tok[1] == "EOF":
            raise ErroSintatico(
                f"Fim inesperado do arquivo — esperava "
                f"'{valor_esp or tipo_esp}'"
            )

        if valor_esp is not None and tok[0] != valor_esp:
            raise ErroSintatico(
                f"[{self.info()}] Esperava '{valor_esp}', "
                f"encontrou '{tok[0]}'"
            )

        if tipo_esp is not None and tok[1] != tipo_esp:
            raise ErroSintatico(
                f"[{self.info()}] Esperava {tipo_esp}, "
                f"encontrou '{tok[0]}' ({tok[1]})"
            )

        self.pos += 1

        return tok

    def registrar(self, erro):
        self.erros.append(erro)

    # ──────────────────────────────────────────────────────────────
    # RECUPERAÇÃO
    # ──────────────────────────────────────────────────────────────

    def sincronizar_stmt(self):

        while self.tipo() != "EOF":

            if self.vv(";"):
                return

            if self.vv("}"):
                return

            self.pos += 1

    def sincronizar_bloco(self):

        profundidade = 0

        while self.tipo() != "EOF":

            if self.vv("{"):
                profundidade += 1

            elif self.vv("}"):

                if profundidade == 0:
                    return

                profundidade -= 1

                if profundidade == 0:
                    self.pos += 1
                    return

            self.pos += 1

    # ──────────────────────────────────────────────────────────────
    # PROGRAMA
    # ──────────────────────────────────────────────────────────────

    def parse_programa(self):

        while self.tipo() != "EOF":

            try:

                if self.tt("PREPROCESSADOR"):
                    self.parse_diretiva()
                else:
                    self.parse_decl_global()

            except ErroSintatico as e:

                self.registrar(str(e))

                inicio = self.pos

                self.sincronizar_stmt()

                # evita loop infinito
                if self.pos == inicio:
                    self.pos += 1

    # ──────────────────────────────────────────────────────────────
    # DIRETIVAS
    # ──────────────────────────────────────────────────────────────

    def parse_diretiva(self):

        self.consumir(tipo_esp="PREPROCESSADOR")

        if self.tt(
            "HEADER_SISTEMA",
            "HEADER_ARQUIVO",
            "IDENTIFICADOR",
            "STRING"
        ):
            self.pos += 1
        else:
            raise ErroSintatico(
                f"[{self.info()}] Esperava header "
                f"após diretiva"
            )

    # ──────────────────────────────────────────────────────────────
    # TIPOS
    # ──────────────────────────────────────────────────────────────

    def parse_tipo(self):

        if self.valor() == "struct":

            self.consumir("struct")
            self.consumir(tipo_esp="IDENTIFICADOR")

            return

        if not self.eh_tipo():

            raise ErroSintatico(
                f"[{self.info()}] Esperava tipo, "
                f"encontrou '{self.valor()}'"
            )

        self.pos += 1

    # ──────────────────────────────────────────────────────────────
    # DECLARAÇÕES
    # ──────────────────────────────────────────────────────────────

    def parse_decl_global(self):

        if not self.eh_tipo():

            raise ErroSintatico(
                f"[{self.info()}] Esperava declaração, "
                f"encontrou '{self.valor()}'"
            )

        i = self.pos

        self.parse_tipo()

        while self.vv("*"):
            self.pos += 1

        if not self.tt("IDENTIFICADOR"):

            raise ErroSintatico(
                f"[{self.info()}] Esperava identificador"
            )

        self.pos += 1

        eh_funcao = self.vv("(")

        self.pos = i

        if eh_funcao:
            self.parse_decl_funcao()
        else:
            self.parse_decl_var()
            self.consumir(";")

    def parse_decl_funcao(self):

        self.parse_tipo()

        while self.vv("*"):
            self.consumir("*")

        self.consumir(tipo_esp="IDENTIFICADOR")

        self.consumir("(")

        self.parse_params()

        self.consumir(")")

        if self.vv(";"):
            self.consumir(";")
        else:
            self.parse_bloco()

    def parse_params(self):

        if self.vv(")"):
            return

        self.parse_param()

        while self.vv(","):

            self.consumir(",")

            self.parse_param()

    def parse_param(self):

        self.parse_tipo()

        while self.vv("*"):
            self.consumir("*")

        if self.tt("IDENTIFICADOR"):
            self.consumir(tipo_esp="IDENTIFICADOR")

    def parse_decl_var(self):

        self.parse_tipo()

        self.parse_declarador()

        while self.vv(","):

            self.consumir(",")

            self.parse_declarador()

    def parse_declarador(self):

        while self.vv("*"):
            self.consumir("*")

        self.consumir(tipo_esp="IDENTIFICADOR")

        while self.vv("["):

            self.consumir("[")

            if not self.vv("]"):
                self.parse_expr("tamanho do array")

            self.consumir("]")

        if self.tt("ATRIBUICAO"):

            self.consumir(tipo_esp="ATRIBUICAO")

            self.parse_expr("valor de inicialização")

    # ──────────────────────────────────────────────────────────────
    # BLOCOS
    # ──────────────────────────────────────────────────────────────

    def parse_bloco(self):

        self.consumir("{")

        while not self.vv("}") and self.tipo() != "EOF":

            try:
                self.parse_stmt()

            except ErroSintatico as e:

                self.registrar(str(e))

                self.sincronizar_stmt()

                if self.vv(";"):
                    self.pos += 1

        self.consumir("}")

    # ──────────────────────────────────────────────────────────────
    # STATEMENTS
    # ──────────────────────────────────────────────────────────────

    def parse_stmt(self):

        v = self.valor()

        if self.vv("{"):
            self.parse_bloco()

        elif v == "if":
            self.parse_if()

        elif v == "while":
            self.parse_while()

        elif v == "for":
            self._parse_for_seguro()

        elif v == "do":
            self.parse_do()

        elif v == "return":

            self.parse_return()

            self.consumir(";")

        elif self.eh_tipo():

            self.parse_decl_var()

            self.consumir(";")

        elif self.vv(";"):

            self.consumir(";")

        else:

            self.parse_expr()

            self.consumir(";")

    # ──────────────────────────────────────────────────────────────
    # CONTROLE
    # ──────────────────────────────────────────────────────────────

    def parse_if(self):

        self.consumir("if")

        self.consumir("(")

        self.parse_expr("condição do if")

        self.consumir(")")

        self.parse_stmt()

        if self.vv("else"):

            self.consumir("else")

            self.parse_stmt()

    def parse_while(self):

        self.consumir("while")

        self.consumir("(")

        self.parse_expr("condição do while")

        self.consumir(")")

        self.parse_stmt()

    def parse_for(self):

        self.consumir("for")

        self.consumir("(")

        if not self.vv(";"):

            if self.eh_tipo():
                self.parse_decl_var()
            else:
                self.parse_expr("inicialização do for")

        self.consumir(";")

        if not self.vv(";"):
            self.parse_expr("condição do for")

        self.consumir(";")

        if not self.vv(")"):
            self.parse_expr("incremento do for")

        self.consumir(")")

        self.parse_stmt()

    def _parse_for_seguro(self):

        try:
            self.parse_for()

        except ErroSintatico as e:

            self.registrar(str(e))

            inicio = self.pos

            # tenta sincronizar dentro do cabeçalho
            while (
                self.tipo() != "EOF"
                and not self.vv(")")
                and not self.vv("{")
            ):
                self.pos += 1

            if self.vv(")"):
                self.pos += 1

            # tenta consumir o corpo
            if self.vv("{"):
                self.sincronizar_bloco()

            # evita loop infinito
            if self.pos == inicio:
                self.pos += 1

    def parse_do(self):

        self.consumir("do")

        self.parse_stmt()

        self.consumir("while")

        self.consumir("(")

        self.parse_expr("condição do do-while")

        self.consumir(")")

        self.consumir(";")

    def parse_return(self):

        self.consumir("return")

        if not self.vv(";"):
            self.parse_expr("valor de retorno")

    # ──────────────────────────────────────────────────────────────
    # EXPRESSÕES
    # ──────────────────────────────────────────────────────────────

    def parse_expr(self, contexto="expressão"):

        self.parse_atrib(contexto)

    def parse_atrib(self, contexto="expressão"):

        self.parse_logico(contexto)

        if self.tt("ATRIBUICAO"):

            self.consumir(tipo_esp="ATRIBUICAO")

            self.parse_atrib(contexto)

    def parse_logico(self, contexto="expressão"):

        self.parse_comparacao(contexto)

        while self.tt("LOGICA") and self.vv("&&", "||"):

            self.pos += 1

            self.parse_comparacao(contexto)

    def parse_comparacao(self, contexto="expressão"):

        self.parse_adicao(contexto)

        while (
            self.tt("LOGICA")
            and self.vv("==", "!=", "<", ">", "<=", ">=")
        ):

            self.pos += 1

            self.parse_adicao(contexto)

    def parse_adicao(self, contexto="expressão"):

        self.parse_mult(contexto)

        while self.tt("OPERADOR") and self.vv("+", "-"):

            self.pos += 1

            self.parse_mult(contexto)

    def parse_mult(self, contexto="expressão"):

        self.parse_unario(contexto)

        while self.tt("OPERADOR") and self.vv("*", "/"):

            self.pos += 1

            self.parse_unario(contexto)

    def parse_unario(self, contexto="expressão"):

        if (
            self.tt("OPERADOR")
            and self.vv("+", "-", "++", "--", "*", "&")
        ):

            self.pos += 1

            self.parse_unario(contexto)

        elif self.tt("LOGICA") and self.vv("!"):

            self.pos += 1

            self.parse_unario(contexto)

        else:
            self.parse_postfixo(contexto)

    def parse_postfixo(self, contexto="expressão"):

        self.parse_primario(contexto)

        while True:

            if self.tt("OPERADOR") and self.vv("++", "--"):

                self.pos += 1

            elif self.vv("["):

                self.consumir("[")

                self.parse_expr("índice")

                self.consumir("]")

            elif self.vv("("):

                self.consumir("(")

                self.parse_args()

                self.consumir(")")

            elif self.vv("."):

                self.consumir(".")

                self.consumir(tipo_esp="IDENTIFICADOR")

            else:
                break

    def parse_primario(self, contexto="expressão"):

        t = self.tipo()
        v = self.valor()

        if t in {
            "NUMERO_INT",
            "NUMERO_REAL",
            "STRING",
            "CHAR"
        }:

            self.pos += 1

        elif t == "IDENTIFICADOR":

            self.pos += 1

        elif self.vv("("):

            self.consumir("(")

            self.parse_expr()

            self.consumir(")")

        else:

            raise ErroSintatico(
                f"[{self.info()}] Esperava {contexto}, "
                f"mas encontrou '{v}'"
            )

    def parse_args(self):

        if self.vv(")"):
            return

        self.parse_expr()

        while self.vv(","):

            self.consumir(",")

            self.parse_expr()


# ═══════════════════════════════════════════════════════════════════
#  INTERFACE
# ═══════════════════════════════════════════════════════════════════

def analisar_sintatico(tokens):

    parser = Parser(tokens)

    parser.parse_programa()

    if parser.erros:

        print("\n══════════════════════════════════════")
        print("ERROS SINTÁTICOS")
        print("══════════════════════════════════════")

        for erro in parser.erros:
            print(erro)

        print("══════════════════════════════════════\n")

        return False

    print("True")

    return True


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():

    entrada = "main.c"
    saida   = "tokens.txt"

    if len(sys.argv) >= 2:
        entrada = sys.argv[1]

    if len(sys.argv) >= 3:
        saida = sys.argv[2]

    if not os.path.isfile(entrada):

        print(f"Erro: arquivo '{entrada}' não encontrado.")

        sys.exit(1)

    with open(
        entrada,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as f:

        codigo = f.read()

    tokens = analisar(codigo)

    saida_txt = gerar_saida(tokens)

    with open(saida, "w", encoding="utf-8") as f:
        f.write(saida_txt)

    print(f"Léxico concluído: {len(tokens)} tokens → '{saida}'")

    analisar_sintatico(tokens)


if __name__ == "__main__":
    main()
