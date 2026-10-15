    /* LANDSTALKER_ASCII: GENRECOMP_ASCII="300,1000" prints those frames as a letter grid */
    {
        static const char *env; static int env_init;
        if (!env_init) { env = getenv("GENRECOMP_ASCII"); env_init = 1; }
        if (env) {
            char key[24]; snprintf(key, sizeof key, ",%ld,", s_frame_no);
            char list[256]; snprintf(list, sizeof list, ",%s,", env);
            if (strstr(list, key)) {
                uint32_t cols[24]; int n = 0; static char grid[28][81];
                for (int gy = 0; gy < 28; gy++) {
                    for (int gx = 0; gx < 80; gx++) {
                        const uint32_t *px = (const uint32_t *)framebuffer + (gy * 8 + 4) * GEN_RENDER_WIDTH + gx * 4 + 2;
                        uint32_t c = *px & 0xFFFFFF; int k = 0;
                        while (k < n && cols[k] != c) k++;
                        if (k == n && n < 24) cols[n++] = c;
                        grid[gy][gx] = (k < 24) ? (char)('A' + k) : '?';
                    }
                    grid[gy][80] = 0;
                }
                printf("--- ascii frame %ld ---\n", s_frame_no);
                for (int gy = 0; gy < 28; gy++) puts(grid[gy]);
                for (int k = 0; k < n; k++) printf("%c=%06X ", 'A' + k, cols[k]);
                printf("\n");
                {   /* whole-frame colour counts + GPGX's derived drawing state */
                    static unsigned long cnt[24]; uint32_t seen[24]; int m = 0;
                    for (int i = 0; i < GEN_RENDER_WIDTH * GEN_RENDER_HEIGHT; i++) {
                        uint32_t c = ((const uint32_t *)framebuffer)[i] & 0xFFFFFF; int k = 0;
                        while (k < m && seen[k] != c) k++;
                        if (k == m && m < 24) { seen[m] = c; cnt[m] = 0; m++; }
                        if (k < m) cnt[k]++;
                    }
                    printf("pixels:"); for (int k = 0; k < m; k++) printf(" %06X=%lu", seen[k], cnt[k]);
                    printf("\n");
                    extern unsigned short ntab, ntbb, ntwb, satb, hscb, bg_list_index, vc_max, lines_per_frame, playfield_row_mask, vscroll;
                    extern unsigned char hscroll_mask, playfield_shift, playfield_col_mask, odd_frame, im2_flag, interlaced, vdp_pal;
                    extern void (*render_bg)(int); extern void render_bg_m5(int); extern void render_bg_m5_vs(int);
                    printf("state: ntab=%04X ntbb=%04X ntwb=%04X satb=%04X hscb=%04X hmask=%02X pshift=%u pcol=%02X prow=%03X vscroll=%04X vcmax=%u lpf=%u pal=%u im2=%u il=%u bglist=%u render_bg=%s\n",
                           ntab, ntbb, ntwb, satb, hscb, hscroll_mask, playfield_shift, playfield_col_mask, playfield_row_mask, vscroll,
                           vc_max, lines_per_frame, vdp_pal, im2_flag, interlaced, bg_list_index,
                           render_bg == render_bg_m5 ? "m5" : render_bg == render_bg_m5_vs ? "m5_vs" : "OTHER");
                }
                fflush(stdout);
            }
        }
    }
