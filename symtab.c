#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "symtab.h"

SymbolTable *st_create(void)
{
    SymbolTable *st = malloc(sizeof(SymbolTable));
    for (int i = 0; i < ST_SIZE; i++)
        st->buckets[i] = NULL;
    st->count = 0;
    return st;
}

unsigned st_hash(const char *key)
{
    unsigned long h = 5381;
    for (; *key; key++)
        h = h * 33 + (unsigned char)*key;
    return (unsigned)(h % ST_SIZE);
}

STPosition st_search(const SymbolTable *st, const char *name)
{
    STPosition pos = { -1, -1 };
    int bucket = (int)st_hash(name);
    int index = 0;
    for (Symbol *s = st->buckets[bucket]; s != NULL; s = s->next, index++) {
        if (strcmp(s->name, name) == 0) {
            pos.bucket = bucket;
            pos.index = index;
            return pos;
        }
    }
    return pos;
}

STPosition st_add(SymbolTable *st, const char *name, int kind)
{
    STPosition pos = st_search(st, name);
    if (pos.bucket != -1)
        return pos;

    Symbol *node = malloc(sizeof(Symbol));
    node->name = malloc(strlen(name) + 1);
    strcpy(node->name, name);
    node->kind = (SymbolKind)kind;
    node->next = NULL;

    int bucket = (int)st_hash(name);
    int index = 0;
    if (st->buckets[bucket] == NULL) {
        st->buckets[bucket] = node;
    } else {
        Symbol *s = st->buckets[bucket];
        index = 1;
        while (s->next != NULL) {
            s = s->next;
            index++;
        }
        s->next = node;
    }
    st->count++;

    pos.bucket = bucket;
    pos.index = index;
    return pos;
}

int st_write(const SymbolTable *st, const char *path)
{
    FILE *out = fopen(path, "w");
    if (out == NULL)
        return 0;
    fprintf(out, "Symbol Table (hash table, %d buckets, %d symbols)\n\n", ST_SIZE, st->count);
    fprintf(out, "%-10s %-24s %s\n", "position", "symbol", "kind");
    for (int i = 0; i < ST_SIZE; i++) {
        int index = 0;
        for (Symbol *s = st->buckets[i]; s != NULL; s = s->next, index++) {
            char p[32];
            snprintf(p, sizeof p, "(%d, %d)", i, index);
            fprintf(out, "%-10s %-24s %s\n", p, s->name,
                    s->kind == SYM_IDENTIFIER ? "identifier" : "constant");
        }
    }
    fclose(out);
    return 1;
}

void st_destroy(SymbolTable *st)
{
    for (int i = 0; i < ST_SIZE; i++) {
        Symbol *s = st->buckets[i];
        while (s != NULL) {
            Symbol *next = s->next;
            free(s->name);
            free(s);
            s = next;
        }
    }
    free(st);
}
