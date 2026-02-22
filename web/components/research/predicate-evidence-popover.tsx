"use client";

/**
 * PredicateEvidencePopover
 * ========================
 * Inline evidence popover for the predicate comparison table.
 * Triggers on click of any table cell and anchors to the clicked element.
 *
 * Features:
 *   - Popover anchored to the trigger element (not modal, not full-screen)
 *   - Source section, quote excerpt (≤ 300 chars), document type badge,
 *     page reference, copy-citation button, open-document button
 *   - Keyboard: Escape closes, Tab cycles within popover (focus trap)
 *   - WCAG AA: role="dialog", aria-modal, aria-labelledby, aria-describedby
 *   - Design tokens: FDA Blue #005EA2, Success #1A7F4B, Warning #B45309
 *   - Dark mode via CSS custom properties from globals.css
 */

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useId,
} from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

/** Document type values that appear as coloured badges. */
export type EvidenceDocumentType =
  | "510(k) Summary"
  | "FDA Guidance"
  | "MAUDE Report"
  | "Clinical Study";

/** Full citation format for copy-to-clipboard. */
export type CitationFormat = "ieee" | "apa";

/**
 * Structured evidence record for a single predicate comparison table cell.
 * Pass this via the `evidence` prop on a table cell trigger.
 */
export interface PredicateEvidence {
  /** Human-readable section reference, e.g. "510(k) Summary §4.2.3 — Performance Testing" */
  sourceSection: string;

  /** Up to 300-character verbatim excerpt from the source document. Will be truncated with "..." if longer. */
  quoteExcerpt: string;

  /** Categorised document type for the badge. */
  documentType: EvidenceDocumentType;

  /** Page reference or section reference, e.g. "Page 12 of 47" or "§III.A" */
  pageReference: string;

  /**
   * Document title used in citation generation.
   * e.g. "SmartFlow Infusion Pump Pro 510(k) Summary"
   */
  documentTitle: string;

  /**
   * Document identifier: K-number, FDA docket number, DOI, etc.
   * e.g. "K231045" or "FDA-2014-D-0798"
   */
  documentReference: string;

  /** Year or date string for citation, e.g. "2023" or "2023-04-15" */
  documentYear?: string;

  /** Author or organisation, e.g. "MedDevice Corp" or "U.S. Food and Drug Administration" */
  documentAuthor?: string;

  /** Full URL to the source document. When absent, the open-document button is hidden. */
  documentUrl?: string;
}

export interface EvidencePopoverProps {
  /** The evidence data to display in the popover. */
  evidence: PredicateEvidence;

  /**
   * The element that triggers the popover.
   * Typically a table cell or a clickable span within one.
   * The popover anchors to this element.
   */
  children: React.ReactNode;

  /** Default citation format for the copy button. Defaults to "ieee". */
  defaultCitationFormat?: CitationFormat;

  /** Controlled open state. When provided, the component acts as a controlled popover. */
  open?: boolean;

  /** Fires when the popover requests to close (Escape key, outside click). */
  onOpenChange?: (open: boolean) => void;

  /** Additional class names applied to the trigger wrapper. */
  className?: string;

  /** Additional class names applied to the popover panel. */
  popoverClassName?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────

const BADGE_CONFIG: Record<
  EvidenceDocumentType,
  { bg: string; text: string; border: string }
> = {
  "510(k) Summary": {
    bg:     "bg-[#005EA2]/10",
    text:   "text-[#005EA2]",
    border: "border-[#005EA2]/30",
  },
  "FDA Guidance": {
    bg:     "bg-[#1A7F4B]/10",
    text:   "text-[#1A7F4B]",
    border: "border-[#1A7F4B]/30",
  },
  "MAUDE Report": {
    bg:     "bg-[#B45309]/10",
    text:   "text-[#B45309]",
    border: "border-[#B45309]/30",
  },
  "Clinical Study": {
    bg:     "bg-purple-500/10",
    text:   "text-purple-600 dark:text-purple-400",
    border: "border-purple-500/30",
  },
};

/** Max excerpt length before truncation. */
const MAX_EXCERPT_CHARS = 300;

// ── Citation generation ────────────────────────────────────────────────────

function buildIeeeCitation(evidence: PredicateEvidence): string {
  const author = evidence.documentAuthor ?? "U.S. Food and Drug Administration";
  const year   = evidence.documentYear ?? new Date().getFullYear().toString();
  const ref    = evidence.documentReference;
  const title  = evidence.documentTitle;
  const page   = evidence.pageReference;
  return `${author}, "${title}," ${ref}, ${year}. [${page}]`;
}

function buildApaCitation(evidence: PredicateEvidence): string {
  const author = evidence.documentAuthor ?? "U.S. Food and Drug Administration";
  const year   = evidence.documentYear ?? new Date().getFullYear().toString();
  const ref    = evidence.documentReference;
  const title  = evidence.documentTitle;
  const url    = evidence.documentUrl ?? "";
  return `${author}. (${year}). ${title} (${ref}). ${url}`.trim().replace(/\.$/, "") + ".";
}

function buildCitation(evidence: PredicateEvidence, format: CitationFormat): string {
  return format === "ieee"
    ? buildIeeeCitation(evidence)
    : buildApaCitation(evidence);
}

// ── Focus trap hook ────────────────────────────────────────────────────────

/**
 * Traps Tab / Shift+Tab focus within the provided container ref.
 * Active only when `active` is true.
 */
function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>, active: boolean) {
  useEffect(() => {
    if (!active || !containerRef.current) return;

    const container = containerRef.current;
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");

    function getFocusable(): HTMLElement[] {
      return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors));
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      const focusable = getFocusable();
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last  = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    container.addEventListener("keydown", handleKeyDown);
    return () => container.removeEventListener("keydown", handleKeyDown);
  }, [active, containerRef]);
}

// ── Popover positioning hook ───────────────────────────────────────────────

type PopoverPlacement = "bottom-start" | "bottom-end" | "top-start" | "top-end";

interface PopoverPosition {
  top:       number;
  left:      number;
  placement: PopoverPlacement;
}

/**
 * Calculates popover position anchored to the trigger element.
 * Automatically flips to avoid viewport overflow.
 */
function usePopoverPosition(
  triggerRef: React.RefObject<HTMLElement | null>,
  popoverRef: React.RefObject<HTMLElement | null>,
  open: boolean,
): PopoverPosition {
  const [position, setPosition] = useState<PopoverPosition>({
    top: 0,
    left: 0,
    placement: "bottom-start",
  });

  const calculate = useCallback(() => {
    if (!triggerRef.current || !popoverRef.current) return;

    const triggerRect  = triggerRef.current.getBoundingClientRect();
    const popoverRect  = popoverRef.current.getBoundingClientRect();
    const viewportW    = window.innerWidth;
    const viewportH    = window.innerHeight;
    const scrollX      = window.scrollX;
    const scrollY      = window.scrollY;
    const GAP          = 6; // px gap between trigger and popover

    // Determine vertical placement
    const spaceBelow = viewportH - triggerRect.bottom;
    const spaceAbove = triggerRect.top;
    const placeAbove = spaceBelow < popoverRect.height + GAP && spaceAbove > spaceBelow;

    // Determine horizontal placement
    const spaceRight = viewportW - triggerRect.left;
    const placeRight = spaceRight >= popoverRect.width;

    const top = placeAbove
      ? triggerRect.top  + scrollY - popoverRect.height - GAP
      : triggerRect.bottom + scrollY + GAP;

    const left = placeRight
      ? triggerRect.left + scrollX
      : triggerRect.right + scrollX - popoverRect.width;

    const placement: PopoverPlacement = placeAbove
      ? (placeRight ? "top-start" : "top-end")
      : (placeRight ? "bottom-start" : "bottom-end");

    setPosition({ top, left, placement });
  }, [triggerRef, popoverRef]);

  useEffect(() => {
    if (!open) return;
    // Run immediately, then again after paint so popoverRect is available.
    calculate();
    const frame = requestAnimationFrame(calculate);
    return () => cancelAnimationFrame(frame);
  }, [open, calculate]);

  return position;
}

// ── CopyButton ─────────────────────────────────────────────────────────────

function CopyButton({
  textToCopy,
  label,
  className,
}: {
  textToCopy: string;
  label: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable — degrade gracefully (e.g. non-secure context)
      console.warn("Clipboard write failed; user must copy manually.");
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={copied ? "Citation copied to clipboard" : label}
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium",
        "border transition-colors cursor-pointer select-none",
        copied
          ? "border-[#1A7F4B]/40 bg-[#1A7F4B]/10 text-[#1A7F4B]"
          : "border-border bg-background text-muted-foreground hover:border-[#005EA2]/40 hover:text-[#005EA2] hover:bg-[#005EA2]/5",
        className,
      )}
    >
      {copied ? (
        <>
          {/* Checkmark icon */}
          <svg
            aria-hidden="true"
            width="11" height="11"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="2,6 5,9 10,3" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          {/* Clipboard icon */}
          <svg
            aria-hidden="true"
            width="11" height="11"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="4" y="1" width="6" height="8" rx="1" />
            <path d="M2 4H1a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-1" />
          </svg>
          Copy citation
        </>
      )}
    </button>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function PredicateEvidencePopover({
  evidence,
  children,
  defaultCitationFormat = "ieee",
  open: controlledOpen,
  onOpenChange,
  className,
  popoverClassName,
}: EvidencePopoverProps) {
  const uid = useId();
  const titleId = `${uid}-title`;
  const bodyId  = `${uid}-body`;

  // Uncontrolled open state (used when `open` prop is not provided)
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;

  const [citationFormat, setCitationFormat] = useState<CitationFormat>(defaultCitationFormat);

  const triggerRef = useRef<HTMLSpanElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Popover position calculated on open
  const position = usePopoverPosition(triggerRef, popoverRef, isOpen);

  // Focus trap active when popover is open
  useFocusTrap(popoverRef, isOpen);

  // ── Open / close helpers ──

  function openPopover() {
    if (isControlled) {
      onOpenChange?.(true);
    } else {
      setInternalOpen(true);
    }
  }

  function closePopover() {
    if (isControlled) {
      onOpenChange?.(false);
    } else {
      setInternalOpen(false);
    }
    // Return focus to trigger when closing
    triggerRef.current?.focus();
  }

  function togglePopover() {
    if (isOpen) closePopover();
    else openPopover();
  }

  // ── Keyboard: Escape closes ──

  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        closePopover();
      }
    }

    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // ── Click outside closes ──

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(e: PointerEvent) {
      const target = e.target as Node;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        closePopover();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // ── Auto-focus first focusable element when popover opens ──

  useEffect(() => {
    if (!isOpen || !popoverRef.current) return;
    const firstFocusable = popoverRef.current.querySelector<HTMLElement>(
      "button:not([disabled]), a[href], [tabindex]:not([tabindex='-1'])"
    );
    firstFocusable?.focus();
  }, [isOpen]);

  // ── Truncate excerpt ──

  const excerpt =
    evidence.quoteExcerpt.length > MAX_EXCERPT_CHARS
      ? evidence.quoteExcerpt.slice(0, MAX_EXCERPT_CHARS) + "..."
      : evidence.quoteExcerpt;

  const badge = BADGE_CONFIG[evidence.documentType];
  const citation = buildCitation(evidence, citationFormat);

  return (
    <>
      {/* Trigger wrapper — inline so it can anchor to a table cell */}
      <span
        ref={triggerRef}
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls={isOpen ? `${uid}-popover` : undefined}
        onClick={togglePopover}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            togglePopover();
          }
        }}
        className={cn(
          "inline cursor-pointer rounded focus-visible:outline-none",
          "focus-visible:ring-2 focus-visible:ring-[#005EA2] focus-visible:ring-offset-1",
          isOpen && "ring-2 ring-[#005EA2]/40 ring-offset-1",
          className,
        )}
      >
        {children}
      </span>

      {/* Popover panel — rendered in document flow via fixed positioning */}
      {isOpen && (
        <div
          id={`${uid}-popover`}
          ref={popoverRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={bodyId}
          style={{
            position: "fixed",
            top:  position.top,
            left: position.left,
            zIndex: 9999,
          }}
          className={cn(
            "w-[360px] max-w-[calc(100vw-24px)]",
            "rounded-xl border border-border bg-card shadow-xl",
            "ring-1 ring-black/5 dark:ring-white/10",
            "animate-in fade-in-0 zoom-in-95 duration-150",
            popoverClassName,
          )}
        >
          {/* Header: source section + close button */}
          <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3 border-b border-border">
            <div className="flex-1 min-w-0">
              {/* Document type badge */}
              <span
                className={cn(
                  "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border mb-2",
                  badge.bg,
                  badge.text,
                  badge.border,
                )}
              >
                {evidence.documentType}
              </span>

              {/* Source section */}
              <p
                id={titleId}
                className="text-[12px] font-semibold text-foreground leading-tight"
              >
                {evidence.sourceSection}
              </p>
            </div>

            {/* Close button */}
            <button
              type="button"
              onClick={closePopover}
              aria-label="Close evidence popover"
              className={cn(
                "flex-shrink-0 w-6 h-6 rounded flex items-center justify-center mt-0.5",
                "text-muted-foreground hover:text-foreground hover:bg-muted",
                "transition-colors cursor-pointer",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#005EA2] focus-visible:ring-offset-1",
              )}
            >
              <svg
                aria-hidden="true"
                width="12" height="12"
                viewBox="0 0 12 12"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <line x1="1" y1="1" x2="11" y2="11" />
                <line x1="11" y1="1" x2="1" y2="11" />
              </svg>
            </button>
          </div>

          {/* Body: quote excerpt + page reference */}
          <div id={bodyId} className="px-4 py-3 space-y-3">
            {/* Quote excerpt */}
            <blockquote className="relative pl-3 border-l-2 border-[#005EA2]/40">
              <p className="text-[12px] text-foreground leading-relaxed italic">
                &ldquo;{excerpt}&rdquo;
              </p>
            </blockquote>

            {/* Page reference */}
            <div className="flex items-center gap-2">
              {/* Page icon */}
              <svg
                aria-hidden="true"
                width="12" height="12"
                viewBox="0 0 12 12"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                className="text-muted-foreground flex-shrink-0"
              >
                <rect x="1" y="1" width="10" height="10" rx="1.5" />
                <line x1="3" y1="4" x2="9" y2="4" />
                <line x1="3" y1="6.5" x2="9" y2="6.5" />
                <line x1="3" y1="9" x2="6" y2="9" />
              </svg>
              <span className="text-[11px] text-muted-foreground font-mono">
                {evidence.pageReference}
              </span>
            </div>

            {/* Citation format toggle */}
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-muted-foreground">Format:</span>
              {(["ieee", "apa"] as CitationFormat[]).map((fmt) => (
                <button
                  key={fmt}
                  type="button"
                  onClick={() => setCitationFormat(fmt)}
                  aria-pressed={citationFormat === fmt}
                  className={cn(
                    "text-[10px] px-2 py-0.5 rounded border font-mono transition-colors cursor-pointer",
                    citationFormat === fmt
                      ? "border-[#005EA2]/50 bg-[#005EA2]/10 text-[#005EA2]"
                      : "border-border text-muted-foreground hover:bg-muted",
                  )}
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Citation preview */}
            <div className="bg-muted/50 rounded-lg px-3 py-2 border border-border">
              <p className="text-[10px] text-muted-foreground leading-relaxed font-mono break-words">
                {citation}
              </p>
            </div>
          </div>

          {/* Footer: copy citation + open document */}
          <div className="px-4 pb-4 flex items-center gap-2">
            <CopyButton
              textToCopy={citation}
              label={`Copy ${citationFormat.toUpperCase()} citation to clipboard`}
            />

            {evidence.documentUrl && (
              <a
                href={evidence.documentUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Open ${evidence.documentTitle} in a new tab`}
                className={cn(
                  "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium",
                  "border border-border bg-background text-muted-foreground",
                  "hover:border-[#005EA2]/40 hover:text-[#005EA2] hover:bg-[#005EA2]/5",
                  "transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#005EA2] focus-visible:ring-offset-1",
                )}
              >
                {/* External link icon */}
                <svg
                  aria-hidden="true"
                  width="11" height="11"
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 2H2a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7" />
                  <path d="M7 1h4v4" />
                  <line x1="11" y1="1" x2="5" y2="7" />
                </svg>
                Open document
              </a>
            )}
          </div>

          {/* Visual arrow indicator — placement-aware */}
          {(position.placement === "bottom-start" || position.placement === "bottom-end") && (
            <div
              aria-hidden="true"
              className="absolute -top-[5px] left-4 w-2.5 h-2.5 rotate-45 border-l border-t border-border bg-card"
            />
          )}
          {(position.placement === "top-start" || position.placement === "top-end") && (
            <div
              aria-hidden="true"
              className="absolute -bottom-[5px] left-4 w-2.5 h-2.5 rotate-45 border-r border-b border-border bg-card"
            />
          )}
        </div>
      )}
    </>
  );
}

// ── Convenience export: hook for use in table cell onClick handlers ─────────

/**
 * useEvidencePopover
 *
 * Manages open state and the currently active evidence record for a table
 * that has many cells, each with its own evidence data.
 *
 * @example
 * ```tsx
 * const { openEvidence, activeEvidence, isOpen, close } = useEvidencePopover();
 *
 * // In a table cell:
 * <PredicateEvidencePopover
 *   evidence={activeEvidence ?? FALLBACK}
 *   open={isOpen && activeEvidence?.sourceSection === cell.evidence.sourceSection}
 *   onOpenChange={(v) => { if (!v) close(); }}
 * >
 *   <span onClick={() => openEvidence(cell.evidence)}>
 *     {cell.value}
 *   </span>
 * </PredicateEvidencePopover>
 * ```
 */
export function useEvidencePopover() {
  const [activeEvidence, setActiveEvidence] = useState<PredicateEvidence | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const openEvidence = useCallback((evidence: PredicateEvidence) => {
    setActiveEvidence(evidence);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  return { openEvidence, activeEvidence, isOpen, close, setIsOpen };
}

// ── Integration example (see bottom of file) ───────────────────────────────
// See "Integration with PredicateComparisonTable" section below the export.

/**
 * EvidenceCellTrigger
 *
 * Thin wrapper that combines a table cell value with its evidence popover.
 * Designed for use inside the predicate comparison table rows.
 *
 * @example
 * ```tsx
 * <td>
 *   <EvidenceCellTrigger
 *     value="Peristaltic pump, ±2% flow accuracy"
 *     evidence={{
 *       sourceSection: "510(k) Summary §4.2.3 — Performance Testing",
 *       quoteExcerpt: "Flow accuracy testing per IEC 60601-2-24 demonstrated...",
 *       documentType: "510(k) Summary",
 *       pageReference: "Page 12 of 47",
 *       documentTitle: "SmartFlow Infusion Pump Pro 510(k) Summary",
 *       documentReference: "K231045",
 *       documentYear: "2023",
 *       documentAuthor: "MedDevice Corp",
 *       documentUrl: "https://www.accessdata.fda.gov/cdrh_docs/pdf23/K231045.pdf",
 *     }}
 *   />
 * </td>
 * ```
 */
export function EvidenceCellTrigger({
  value,
  evidence,
  className,
}: {
  value: React.ReactNode;
  evidence: PredicateEvidence;
  className?: string;
}) {
  return (
    <PredicateEvidencePopover evidence={evidence} className={className}>
      <span
        className={cn(
          "inline-flex items-center gap-1 group cursor-pointer",
          "underline decoration-dotted decoration-[#005EA2]/40 underline-offset-2",
          "hover:decoration-[#005EA2] hover:text-[#005EA2] transition-colors",
        )}
        title="Click to view evidence source"
      >
        {value}
        {/* Evidence indicator dot */}
        <span
          aria-hidden="true"
          className={cn(
            "w-1.5 h-1.5 rounded-full flex-shrink-0",
            "bg-[#005EA2]/40 group-hover:bg-[#005EA2]",
            "transition-colors",
          )}
        />
      </span>
    </PredicateEvidencePopover>
  );
}

/*
 * ─────────────────────────────────────────────────────────────────────────────
 * Integration with PredicateComparisonTable in web/app/research/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * The component is designed to wrap any table cell value in the predicate
 * comparison table. Here is how to wire it into the existing Predicates tab:
 *
 * 1. Import the components:
 *
 *    import {
 *      EvidenceCellTrigger,
 *      type PredicateEvidence,
 *    } from "@/components/research/predicate-evidence-popover";
 *
 * 2. Add an evidence map to your predicate data. In production, this comes
 *    from the bridge API (evidence chain from the EvidenceChainViewer data):
 *
 *    const EVIDENCE_MAP: Record<string, Record<string, PredicateEvidence>> = {
 *      "K231045": {
 *        "Pumping Mechanism": {
 *          sourceSection: "510(k) Summary §4.2.3 — Performance Testing",
 *          quoteExcerpt: "Flow accuracy testing per IEC 60601-2-24 demonstrated ±1.8% ...",
 *          documentType: "510(k) Summary",
 *          pageReference: "Page 12 of 47",
 *          documentTitle: "SmartFlow Infusion Pump Pro 510(k) Summary",
 *          documentReference: "K231045",
 *          documentYear: "2023",
 *          documentAuthor: "MedDevice Corp",
 *          documentUrl: "https://www.accessdata.fda.gov/cdrh_docs/pdf23/K231045.pdf",
 *        },
 *      },
 *    };
 *
 * 3. In the comparison table cell (inside the predicates tab layout):
 *
 *    {comparisonRows.map((row) => (
 *      <tr key={row.id}>
 *        <td className="px-4 py-2 text-[11px] font-medium text-muted-foreground">
 *          {row.label}
 *        </td>
 *        {selectedPredicates.map((pred) => {
 *          const ev = EVIDENCE_MAP[pred.kNumber]?.[row.label];
 *          return (
 *            <td key={pred.kNumber} className="px-4 py-2 text-[11px] text-foreground">
 *              {ev ? (
 *                <EvidenceCellTrigger value={row.values[pred.kNumber]} evidence={ev} />
 *              ) : (
 *                row.values[pred.kNumber]
 *              )}
 *            </td>
 *          );
 *        })}
 *      </tr>
 *    ))}
 *
 * 4. No global state or context provider needed — each EvidenceCellTrigger
 *    manages its own open/close state independently.
 *
 * 5. For a shared single-popover-at-a-time pattern (avoids multiple open
 *    popovers), use the useEvidencePopover() hook at the table level:
 *
 *    const { openEvidence, activeEvidence, isOpen, close } = useEvidencePopover();
 *
 *    Then render a single <PredicateEvidencePopover> outside the table and
 *    call openEvidence(cellEvidence) from each cell's onClick.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 */
