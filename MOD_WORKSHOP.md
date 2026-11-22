# Mod Workshop: correct the texts of your language

Project-Friday is translated with the help of AI, and native speakers can do it better. The **Mod Workshop** lets you change any text of the game in your language without editing program files. Your changes stay on your computer, updates never overwrite them, and you can send them to us so every player gets them.

## 1. Find the Mods folder
Start the game once (version 1.9.11 or newer). It creates its Mods folder:

| You play with | Mods folder |
|---|---|
| Steam Deck / Linux (AppImage) | `Project-Friday Mods`, in the same folder as the AppImage file |
| Windows installer | `Mods` in the folder you installed to (by default `%LOCALAPPDATA%\Programs\Project-Friday\Mods`) |
| Windows zip | `Mods` inside the extracted Project-Friday folder |

Inside are the page `Mod Workshop.html` and the folder `lang` (your changed texts).

## 2. Change texts
1. **Open `Mod Workshop.html`** with a double click. It opens in your browser (Chrome, Edge or Firefox) and works offline; nothing is sent anywhere.
2. **Pick your language** at the top.
3. **Find the text:** search by word, or use the filter: dialogue, names / menus, map areas, items, options menu, Friday hints, texts not translated yet, your changes.
4. **Type the new text in the right column.** The columns show the original English (from your own ROM) and the current text. Leave a field empty to keep the current text.
   - Keep the codes in braces as in the English text: `{SoftNewLine}` line break, `{ContinuePrompt}` wait for a button, `{Speaker}` the speaker's name, `{=name}` a character name (follows *Options > Names*). Line breaks and pauses may move.
   - A text marked **red** would be refused by the game; the reason is shown below it.
   - Unsaved changes stay in your browser until you save.
5. **Save.**
   - **Chrome / Edge:** the first time, the browser asks for a folder: choose the **Mods folder**. The page then saves straight into it.
   - **Firefox:** the file `<language>.json` (for example `ru.json`) goes to your Downloads. Move it into the `lang` folder inside the Mods folder (replace the old file).
6. **Start the game again.** Your texts are in.

To undo a change, empty its field and save again. To undo all changes of a language, delete its file in `lang`.

## 3. Send us your corrections
Please open a [GitHub issue](https://github.com/cmdrlucid/Project-Friday/issues) and attach your file (`lang/<language>.json` in the Mods folder). We put your corrections into the game, so every player gets them with the next version. With **Import** on the page you can also load a file somebody else sent you, check it and save it.

The page is rewritten by the game when a new version brings new texts; your files in `lang` are never changed.
