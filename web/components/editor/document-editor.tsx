/**
 * FDA-250  [FE-012] Document Studio — TipTap Rich Text Editor
 * ============================================================
 * Production-grade 510(k) section editor with:
 *  - TipTap 2.x with StarterKit (bold, italic, headings, lists, code, blockquote)
 *  - Highlight extension for AI suggestion overlays
 *  - Underline + Typography extensions for professional text
 *  - Character/word count indicator
 *  - Formatting toolbar with accessible icon buttons
 *  - Auto-save debounce (2s) — calls onSave(html) when content settles
 *  - Placeholder text per section type
 *  - Stale / saved / saving indicator
 *
 * Dependencies (requires npm install):
 *  @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
 *  @tiptap/extension-character-count @tiptap/extension-highlight
 *  @tiptap/extension-typography @tiptap/extension-underline
 */

"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import { useEditor, EditorContent }              from "@tiptap/react";
import StarterKit                                from "@tiptap/starter-kit";
import Placeholder                               from "@tiptap/extension-placeholder";
import CharacterCount                            from "@tiptap/extension-character-count";
import Highlight                                 from "@tiptap/extension-highlight";
import Typography                                from "@tiptap/extension-typography";
import Underline                                 from "@tiptap/extension-underline";
import {
  Bold, Italic, Underline as UnderlineIcon,
  Heading2, Heading3, List, ListOrdered, Quote, Code, Minus,
  Undo2, Redo2, Save, CheckCircle2, Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge }  from "@/components/ui/badge";

// ── Section placeholder text ──────────────────────────────────────────────────

const SECTION_PLACEHOLDERS: Record<string, string> = {
  "intended-use":    "Describe the intended use of the device…",
  "device-desc":     "Provide a detailed description of the device…",
  "substantial-equiv": "Establish substantial equivalence to the predicate device…",
  "performance-testing": "Summarize performance testing results…",
  "biocompatibility": "Describe biocompatibility evaluation per ISO 10993…",
  "sterility":       "Describe sterilization method and validation…",
  "labeling":        "Describe labeling, IFU, and warnings…",
  default:           "Begin writing this section…",
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DocumentEditorProps {
  /** Initial HTML content */
  initialContent?: string;
  /** Section type for placeholder text selection */
  sectionType?:    string;
  /** Called with serialized HTML when content settles (2s debounce) */
  onSave?:         (html: string) => Promise<void> | void;
  /** Called on every content change */
  onChange?:       (html: string) => void;
  /** If true, editor is read-only */
  readOnly?:       boolean;
}

// ── Toolbar button ────────────────────────────────────────────────────────────

function ToolbarBtn({
  onClick,
  active,
  disabled,
  title,
  children,
}: {
  onClick:   () => void;
  active?:   boolean;
  disabled?: boolean;
  title:     string;
  children:  React.ReactNode;
}) {
  return (
    <button
      onMouseDown={(e) => { e.preventDefault(); onClick(); }}
      disabled={disabled}
      title={title}
      className={[
        "flex h-7 w-7 items-center justify-center rounded text-sm transition-colors",
        active   ? "bg-foreground text-background"   : "hover:bg-muted",
        disabled ? "pointer-events-none opacity-30"  : "",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

// ── Divider ───────────────────────────────────────────────────────────────────

function ToolbarDivider() {
  return <div className="mx-0.5 h-5 w-px bg-border" />;
}

// ── Save status indicator ─────────────────────────────────────────────────────

type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error";

function SaveIndicator({ status }: { status: SaveStatus }) {
  if (status === "idle") return null;
  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      {status === "pending" && <><Clock className="h-3 w-3 animate-pulse" /> Unsaved</>}
      {status === "saving"  && <><Clock className="h-3 w-3 animate-spin" />  Saving…</>}
      {status === "saved"   && <><CheckCircle2 className="h-3 w-3 text-green-500" /> Saved</>}
      {status === "error"   && <><span className="text-destructive">Save failed</span></>}
    </div>
  );
}

// ── Main editor component ─────────────────────────────────────────────────────

export function DocumentEditor({
  initialContent = "",
  sectionType    = "default",
  onSave,
  onChange,
  readOnly       = false,
}: DocumentEditorProps) {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const placeholder = SECTION_PLACEHOLDERS[sectionType] ?? SECTION_PLACEHOLDERS.default;

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({ placeholder }),
      CharacterCount,
      Highlight.configure({ multicolor: false }),
      Typography,
      Underline,
    ],
    content:  initialContent || "",
    editable: !readOnly,
    onUpdate({ editor }) {
      const html = editor.getHTML();
      onChange?.(html);
      setSaveStatus("pending");

      // Debounced auto-save
      if (saveTimer.current) clearTimeout(saveTimer.current);
      if (onSave) {
        saveTimer.current = setTimeout(async () => {
          setSaveStatus("saving");
          try {
            await onSave(html);
            setSaveStatus("saved");
            setTimeout(() => setSaveStatus("idle"), 3000);
          } catch {
            setSaveStatus("error");
          }
        }, 2000);
      }
    },
  });

  // Update content when prop changes (e.g. AI suggestion applied)
  useEffect(() => {
    if (editor && initialContent && editor.getHTML() !== initialContent) {
      editor.commands.setContent(initialContent, false);
    }
  }, [editor, initialContent]);

  // Cleanup timer on unmount
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

  const manualSave = useCallback(async () => {
    if (!editor || !onSave) return;
    setSaveStatus("saving");
    try {
      await onSave(editor.getHTML());
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    }
  }, [editor, onSave]);

  if (!editor) return null;

  const charCount = editor.storage.characterCount?.characters?.() ?? 0;
  const wordCount = editor.storage.characterCount?.words?.()      ?? 0;

  return (
    <div className="flex flex-col rounded-xl border shadow-sm">
      {/* ── Formatting toolbar ── */}
      {!readOnly && (
        <div className="flex flex-wrap items-center gap-0.5 border-b bg-muted/30 px-2 py-1.5">
          {/* Text style */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive("bold")}
            title="Bold (Ctrl+B)"
          >
            <Bold className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive("italic")}
            title="Italic (Ctrl+I)"
          >
            <Italic className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            active={editor.isActive("underline")}
            title="Underline (Ctrl+U)"
          >
            <UnderlineIcon className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            active={editor.isActive("highlight")}
            title="Highlight"
          >
            <span className="text-[10px] font-bold">H</span>
          </ToolbarBtn>

          <ToolbarDivider />

          {/* Headings */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive("heading", { level: 2 })}
            title="Heading 2"
          >
            <Heading2 className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive("heading", { level: 3 })}
            title="Heading 3"
          >
            <Heading3 className="h-3.5 w-3.5" />
          </ToolbarBtn>

          <ToolbarDivider />

          {/* Lists */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive("bulletList")}
            title="Bullet list"
          >
            <List className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive("orderedList")}
            title="Numbered list"
          >
            <ListOrdered className="h-3.5 w-3.5" />
          </ToolbarBtn>

          <ToolbarDivider />

          {/* Block elements */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive("blockquote")}
            title="Blockquote"
          >
            <Quote className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleCode().run()}
            active={editor.isActive("code")}
            title="Inline code"
          >
            <Code className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            title="Horizontal rule"
          >
            <Minus className="h-3.5 w-3.5" />
          </ToolbarBtn>

          <ToolbarDivider />

          {/* History */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo (Ctrl+Z)"
          >
            <Undo2 className="h-3.5 w-3.5" />
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo (Ctrl+Y)"
          >
            <Redo2 className="h-3.5 w-3.5" />
          </ToolbarBtn>

          {/* Save status + manual save */}
          <div className="ml-auto flex items-center gap-2">
            <SaveIndicator status={saveStatus} />
            {onSave && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={manualSave}
                disabled={saveStatus === "saving"}
              >
                <Save className="h-3.5 w-3.5" />
                Save
              </Button>
            )}
          </div>
        </div>
      )}

      {/* ── Editor body ── */}
      <EditorContent
        editor={editor}
        className="prose prose-sm dark:prose-invert max-w-none flex-1 cursor-text px-6 py-5 focus-within:outline-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[200px] [&_.ProseMirror_p.is-editor-empty:first-child::before]:pointer-events-none [&_.ProseMirror_p.is-editor-empty:first-child::before]:float-left [&_.ProseMirror_p.is-editor-empty:first-child::before]:h-0 [&_.ProseMirror_p.is-editor-empty:first-child::before]:text-muted-foreground [&_.ProseMirror_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]"
      />

      {/* ── Status bar ── */}
      <div className="flex items-center justify-between border-t bg-muted/20 px-4 py-1.5 text-xs text-muted-foreground">
        <span>{wordCount} words · {charCount} characters</span>
        {readOnly && <Badge variant="secondary">Read-only</Badge>}
      </div>
    </div>
  );
}
