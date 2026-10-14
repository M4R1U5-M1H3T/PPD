#ifndef SYMTAB_H
#define SYMTAB_H

#define ST_SIZE 31

typedef enum { SYM_IDENTIFIER = 0, SYM_CONSTANT = 1 } SymbolKind;

typedef struct Symbol {
    char *name;
    SymbolKind kind;
    struct Symbol *next;
} Symbol;

typedef struct {
    Symbol *buckets[ST_SIZE];
    int count;
} SymbolTable;

typedef struct {
    int bucket;
    int index;
} STPosition;

SymbolTable *st_create(void);
unsigned st_hash(const char *key);
STPosition st_search(const SymbolTable *st, const char *name);
STPosition st_add(SymbolTable *st, const char *name, int kind);
int st_write(const SymbolTable *st, const char *path);
void st_destroy(SymbolTable *st);

#endif
