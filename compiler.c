#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>

#define MAX_TOKEN 100

const char *keywords[] = {
    "int", "float", "if", "else", "while", "return", "for", "char", "void", "main", "printf"
};
int num_keywords = 11;

int isKeyword(const char *str) {
    for (int i = 0; i < num_keywords; i++) {
        if (strcmp(str, keywords[i]) == 0)
            return 1;
    }
    return 0;
}

int main() {
    FILE *file = fopen("entrada.txt", "r");
    if (!file) {
        printf("Erro ao abrir arquivo\n");
        return 1;
    }

    char c;
    char token[MAX_TOKEN];
    int i = 0;

    while ((c = fgetc(file)) != EOF) {

        if (isspace(c)) continue;
        
        else if (c == '"') {
    		i = 0;
    		int fechado = 0;

    		while ((c = fgetc(file)) != EOF) {
        		if (c == '"') {
            		fechado = 1;
            		break;
        		}

        		if (c == '\n')
            		break;

        		if (i < MAX_TOKEN - 1)
            	token[i++] = c;
    		}

    		token[i] = '\0';

    		if (fechado)
        		printf("\"%s\" -> TEXTO\n", token);
    		else
        		printf("\"%s -> IRINEU\n", token);
		}

        if (isalpha(c)) {
            i = 0;
            token[i++] = c;

            while (isalnum(c = fgetc(file)) || c == '_') {
                if (i < MAX_TOKEN - 1)
                    token[i++] = c;
            }
            token[i] = '\0';

            if (isKeyword(token)) {
                printf("%s -> PALAVRA-CHAVE\n", token);
            }
            else if (islower(token[0])) {
                printf("%s -> IDENTIFICADOR\n", token);
            }
            else {
                printf("%s -> TEXTO\n", token);
            }

            ungetc(c, file);
        }

        else if (isdigit(c)) {
            i = 0;
            token[i++] = c;

            while (isdigit(c = fgetc(file))) {
                    token[i++] = c;
            }
            token[i] = '\0';

            printf("%s -> NUMERO\n", token);

            ungetc(c, file);
        }

        else if (c == '/') {
            char next = fgetc(file);

            if (next == '/') {
                while ((c = fgetc(file)) != '\n' && c != EOF);
                printf("// -> COMENTARIO\n");
            } else {
                printf("/ -> OPERADOR\n");
                ungetc(next, file);
            }
        }

        else if (strchr("+-*=><", c)) {
            printf("%c -> OPERADOR\n", c);
        }

        else if (strchr("();{}", c)) {
            printf("%c -> DELIMITADOR\n", c);
        }

        else {
            printf("%c -> IRINEU\n", c);
        }
    }

    fclose(file);
    return 0;
}
