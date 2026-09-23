import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

window.CrediclassEditor = {
  create(element, content = "") {
    return new Editor({
      element,
      content,
      extensions: [StarterKit],
      editorProps: { attributes: { class: "crediclass-tiptap-editor" } },
    });
  },
};
