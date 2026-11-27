"""LIGHT PROXY: the ROCK WALL / PLATEAU of room 465 (cliff path above the river; barrier wall pass 2026-11-27, after room 503 = remake/recipes/proxy_rock_503.py).
An invisible shape for the lighting (op 'mesh' + "surface"), GAME coordinates (x east, y south, z up, one map cell = 16), built by remake/lib/rockwall.py.

Why: the cliff behind the walkway (128 path x 22..29 rows 43..62, 176 ledge x 26..27 rows 35..42, 96 / 112 path x 28..35 rows 20..36) is drawn over VOID and
invisible BARRIER ($4F) cells; the light's void painter made them a low water floor = a hole (the sword glow never lit the wall, a hard lit box by the lamp post).
FOOTPRINT = the barrier lines (10 rectangles that hold only void / barrier cells, PIECES; the 160 bush cells, the 144 / 176 steps and the walkway stay outside):
  +x faces x 544 (rows 20..27), 480 (28..34), 416 (35..37, 40..44), 400 (38..39, 45), 384 (46..47), 368 (48, 55..62), 352 (49..54); the void cells 23..24 x 61..62
  beside the exit are left out (no barrier: probably the cliff below the walkway end, not the peak).
TOP: the drawn outline extruded along the view ray (seen edge-on), capped by the PLATEAU at 240 for U >= 736: MEASURED (local helper over tools/romrender.py):
  the plateau's front edges all give 240 = the barrier height (15 x 16): the +y face y 448 (x 480..544) V = U / 2 - 432 + ... (Y - Z = 208), the +x face x 544
  (U 1288..1352: z 240), the grass edge on the y 560 face behind the 176 ledge (Y - Z = 323.5, z ~ 237) and on the x 416 face behind the walkway (z 237..240).
  The LEFT PEAK (U 560..735) stands above the plateau: V = 640 - U / 2 to the pixel = the x 352 face at z 304 (x 368 at 320); its shoulder drops at U 736.
  The right end: the shoulder above the 80 path down to ~100 at U 1406.
  OUTLINE = the topmost drawn pixel of every picture column U 560..1466 (SIL below, upper envelope over 5 columns in rockwall.envelope).
Output: landstalker/data/proxies/rock_465_<piece>.obj (our own geometry, committed). Run: python3 remake/recipes/proxy_rock_465.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import rockwall as RW

SIL_U0 = 560
SIL = [int(v) for v in "360 359 359 358 358 357 357 356 356 355 355 354 354 353 353 352 352 351 351 350 350 349 349 348 348 347 347 346 346 345 345 344 344 343 343 342 342 341 341 340 340 339 339 338 338 337 337 336 336 335 335 334 334 333 333 332 332 331 331 330 330 329 329 328 328 327 327 326 326 325 325 324 324 323 323 322 322 321 321 320 320 319 319 318 318 317 317 316 316 315 315 314 314 313 313 312 312 311 311 310 310 309 309 308 308 307 307 306 306 305 305 304 304 303 303 302 302 301 301 300 300 299 299 298 298 297 297 296 296 295 295 294 294 293 293 292 292 291 291 290 290 289 289 288 288 287 287 286 286 285 285 284 284 283 283 282 282 281 281 280 280 280 280 280 280 280 282 285 285 287 288 289 291 296 296 297 312 313 314 313 314 317 318 325 325 327 328 329 331 329 329 328 328 327 327 326 326 325 325 324 324 323 323 322 322 321 321 320 320 319 319 318 318 317 317 316 316 315 315 314 314 313 313 312 312 311 311 310 310 309 309 308 308 307 307 306 306 305 305 304 304 303 303 302 302 301 301 300 300 299 299 298 298 297 297 296 284 285 282 280 279 278 276 276 275 274 274 272 273 273 272 272 272 272 272 273 271 270 268 268 267 266 266 264 265 265 264 264 264 264 264 265 263 262 260 260 259 258 258 256 257 257 256 256 256 256 256 257 255 254 252 252 251 250 250 248 249 249 248 248 248 248 247 240 239 238 238 237 232 234 231 230 228 226 225 224 224 225 226 228 230 231 230 229 224 226 223 222 220 218 217 216 216 217 218 220 222 223 222 221 216 218 215 214 212 210 209 208 208 209 210 212 214 215 214 213 208 210 207 206 204 202 201 200 200 201 202 204 206 207 206 205 200 202 199 198 196 194 193 192 192 193 194 196 198 199 198 197 192 194 191 190 188 186 185 184 184 185 186 188 190 191 190 189 184 186 183 182 180 178 177 176 176 177 178 180 182 183 182 181 176 178 175 174 172 170 169 168 168 169 170 172 174 175 174 173 168 170 167 166 164 162 161 160 160 161 162 164 166 167 166 165 160 162 159 158 156 154 153 152 152 153 154 156 158 159 158 157 152 154 151 150 148 146 145 144 144 145 146 148 150 151 154 152 157 158 159 158 156 154 153 152 152 153 154 156 158 159 162 160 165 166 167 166 164 162 161 160 160 161 162 164 166 167 170 168 173 174 175 174 172 170 169 168 168 169 170 172 174 175 178 176 181 182 183 182 180 178 177 176 176 177 178 180 182 183 186 184 189 190 191 190 188 186 185 184 184 185 186 188 190 191 194 192 197 198 198 199 200 207 208 208 208 208 209 209 210 211 211 213 212 212 215 213 217 218 217 232 232 233 233 234 234 235 235 236 236 237 237 238 238 239 239 240 240 239 239 238 238 237 237 236 236 235 235 234 234 233 233 232 232 231 231 230 230 229 229 228 228 227 227 226 226 225 225 224 224 225 225 226 226 227 227 228 228 229 229 230 230 231 231 232 232 233 233 234 234 235 235 236 236 237 237 238 238 239 239 240 240 241 241 242 242 243 243 244 244 245 245 246 246 247 247 248 248 249 249 250 250 251 251 252 252 253 253 254 254 255 255 256 256 255 255 254 254 253 253 252 252 251 251 250 250 249 249 248 248 247 247 246 246 245 245 244 244 243 243 242 242 241 241 240 240 239 239 238 238 237 237 236 236 235 235 234 234 233 233 232 232 231 231 230 230 229 229 228 228 227 227 226 226 225 225 224 224 223 223 222 222 221 221 220 220 219 219 218 218 217 217 216 232 233 234 233 234 237 238 245 245 247 248 249 251 256 256 257 272 273 274 273 274 277 278 285 285 287 288 289 291 296 296 297 312 313 314 313 314 317 318 325 325 327 328 329 331 333 334 336 352 351 351 350 350 349 349 348 348 347 347 346 346 345 345 344 344 343 343 342 342 341 341 340 340 339 339 338 338 337 337 336 336 337 337 338 338 339 339 340 340 341 341 342 342 343 343 344 344 345 345 346 346 347 347 348 348 349 349".split()]   # V of the topmost drawn pixel, U = SIL_U0 + index (room 465 picture)
PIECES = {"a": (12, 12, 21, 62), "b": (22, 12, 22, 48), "b2": (22, 55, 22, 62), "c": (23, 12, 24, 45), "c2": (23, 46, 23, 47),
          "d": (25, 12, 25, 37), "d2": (25, 40, 25, 44), "e": (26, 12, 29, 34), "g": (30, 12, 33, 27)}   # cells x0 y0 x1 y1 (inclusive)
U_LEFT, U_RIGHT = 560, 1406
PLATEAU, PEAK_END = 240, 736

E = RW.envelope([(SIL_U0 + i, v) for i, v in enumerate(SIL)])
def vsil(U):
    U = min(max(U, SIL_U0), SIL_U0 + len(SIL) - 1); a = int(U); f = U - a
    return E[a] * (1 - f) + E[min(a + 1, SIL_U0 + len(SIL) - 1)] * f
def cap(U): return None if U < PEAK_END else PLATEAU

ROCK = RW.Rock(vsil, U_LEFT - 1184, U_RIGHT - 1184, cap=cap)

if __name__ == "__main__":
    for k, r in PIECES.items():
        V, F = ROCK.piece(r)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies", "rock_465_%s.obj" % k)
        RW.write_obj(out, V, F, "room 465 rock wall / plateau piece %s (cells %d..%d x %d..%d), light proxy (remake/recipes/proxy_rock_465.py), game coordinates" % (k, r[0], r[2], r[1], r[3]))
        zs = [v[2] for v in V] or [0]
        print("proxy_rock_465 %s: %d vertices, %d triangles, z %.1f..%.1f, inward-facing: %d" % (k, len(V), len(F), min(zs), max(zs), ROCK.orient_bad(V, F, r)))
