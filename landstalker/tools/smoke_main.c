/* CI smoke test (no ROM, no game code): initialise genrecomp, load the dummy ROM (tools/make_dummy_rom.py), run a few frames and shut down,
 * so that the battery RAM file (<rom>.srm) is written on the first run and read again on the second. Built by `zigbuild.py --smoke`. */
#include "genrecomp/genrecomp.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char *argv[]) {
    int i;
    if (argc < 2) { fprintf(stderr, "usage: smoke rom\n"); return 2; }
    fprintf(stderr, "smoke: init\n");
    if (!genrecomp_init("smoke", 1)) { fprintf(stderr, "smoke: init failed\n"); return 3; }
    fprintf(stderr, "smoke: load rom %s\n", argv[1]);
    if (!genrecomp_load_rom(argv[1])) { fprintf(stderr, "smoke: load failed\n"); return 4; }
    fprintf(stderr, "smoke: rom loaded\n");
    for (i = 0; i < 130; i++) { if (!genrecomp_begin_frame()) break; genrecomp_end_frame(); }
    fprintf(stderr, "smoke: frames ok\n");
    genrecomp_shutdown();
    fprintf(stderr, "smoke: ok\n");
    return 0;
}
