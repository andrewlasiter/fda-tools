# Adobe Acrobat Integration Plan for FDA Plugin

## Goal

Enable Claude Code to **automatically attach files to eSTAR PDF forms** via Adobe Acrobat automation, eliminating the manual step of clicking attachment icons.

---

## Architecture: MCP Server for Adobe Acrobat

###

 Option 1: AppleScript/JavaScript for Acrobat (macOS/Windows)

**Capabilities:**
- Open PDF files in Acrobat
- Execute JavaScript within PDF context
- Add file attachments programmatically
- Navigate to specific pages/sections
- Read/write form field values

**Implementation:**

```javascript
// Adobe Acrobat JavaScript API
// Can be executed via AppleScript (macOS) or COM automation (Windows)

// Example: Attach a file to a specific annotation
var doc = this;

// Create file attachment annotation at specific coordinates
var annot = doc.addAnnot({
    page: 14,  // Section 15: Performance Testing (page number)
    type: "FileAttachment",
    point: [100, 700],  // X, Y coordinates
    name: "Performance Test Report",
    cAttachmentPath: "/path/to/Bench_Test_Report.pdf"
});

// Or attach to existing attachment field
doc.importDataObject({
    cName: "Section_15_Attachment",
    cDIPath: "/path/to/Bench_Test_Report.pdf"
});
```

**MCP Server Structure:**

```json
{
  "mcpServers": {
    "adobe-acrobat": {
      "command": "node",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/mcp-servers/adobe-acrobat/index.js"
      ],
      "env": {
        "ACROBAT_PATH": "/Applications/Adobe Acrobat DC/Adobe Acrobat.app"
      }
    }
  }
}
```

**MCP Tools Provided:**

1. **`acrobat_open_pdf`**
   - Opens a PDF in Adobe Acrobat
   - Returns success/failure

2. **`acrobat_attach_file`**
   - Attaches a file to a specific section/page
   - Parameters: pdf_path, attachment_path, page_number, section_name
   - Auto-detects attachment fields by section

3. **`acrobat_list_attachments`**
   - Lists all current attachments in a PDF
   - Returns array of {name, page, path}

4. **`acrobat_remove_attachment`**
   - Removes an attachment by name

5. **`acrobat_batch_attach`**
   - Attaches multiple files from a manifest
   - Input: JSON mapping {section → file_path}

6. **`acrobat_save_pdf`**
   - Saves the PDF with attachments

---

### Option 2: PyPDF2/pikepdf + GUI Automation (Cross-platform)

**Capabilities:**
- Read/write PDF annotations programmatically
- Add file attachments as embedded objects
- No dependency on Adobe Acrobat (uses open-source PDF libraries)
- GUI automation fallback (pyautogui) for fields that require Acrobat

**Pros:**
- No Acrobat license required
- More portable (works on Linux too)
- Full programmatic control

**Cons:**
- Some eSTAR features may require Acrobat (XFA forms)
- Attachment rendering may differ

---

### Option 3: Hybrid Approach (Recommended)

**Use pikepdf for XML import, AppleScript/COM for attachments:**

1. **Import data using CLI** (already working):
   ```bash
   # Import XML into eSTAR PDF
   estar_xml.py generate --project X --output data.xml
   # Use Acrobat's command-line interface (if available)
   ```

2. **Attach files via MCP server**:
   ```
   Claude: "Attach the performance test report to Section 15"
   → MCP call: acrobat_attach_file(
       pdf="submission.pdf",
       file="Bench_Test_Report.pdf",
       section="15"
     )
   → Acrobat JavaScript executes
   → File attached
   ```

---

## Implementation Roadmap

### Phase 1: Basic MCP Server (1-2 days)
- [x] Create MCP server skeleton
- [ ] Implement `acrobat_open_pdf`
- [ ] Implement `acrobat_attach_file` (single file)
- [ ] Test on macOS with AppleScript
- [ ] Test on Windows with COM automation

### Phase 2: Intelligent Attachment Mapping (2-3 days)
- [ ] Build section → page number mapping for each eSTAR template
  ```json
  {
    "nIVD_eSTAR_v6.1": {
      "Section_15_Performance": {"page": 45, "field_id": "PerfTestAttach"},
      "Section_12_Biocompat": {"page": 38, "field_id": "BiocompatAttach"},
      ...
    }
  }
  ```
- [ ] Auto-detect eSTAR template version from PDF
- [ ] Implement `acrobat_batch_attach` with manifest support

### Phase 3: Integration with Plugin (3-4 days)
- [ ] Add `/fda:attach` command
  ```bash
  /fda:attach --estar submission.pdf --manifest attachments.json
  ```
- [ ] Enhance `/fda:assemble` to generate attachment manifest automatically
  ```json
  {
    "Section_15_Performance": [
      "calculations/ASTM_F2077_Static_Compression.pdf",
      "calculations/ASTM_F2077_Fatigue_Testing.pdf"
    ],
    "Section_12_Biocompatibility": [
      "test_reports/ISO_10993-5_Cytotoxicity.pdf",
      "test_reports/ISO_10993-10_Irritation.pdf"
    ],
    "Section_09_Labeling": [
      "labeling/Label_Artwork_All_Configs.pdf",
      "labeling/IFU_Final.pdf"
    ]
  }
  ```
- [ ] Add attachment validation (check file exists, size <100MB, PDF format)

### Phase 4: Agent Integration (2-3 days)
- [ ] Create `attachment-manager` agent
- [ ] Agent capabilities:
  - Read draft files to identify what attachments are needed
  - Check project directory for matching PDFs
  - Prompt user for missing files
  - Execute batch attachment
  - Verify all attachments added successfully

---

## Example Workflow

### Current (Manual):
```
1. User: Generate eSTAR XML
2. Plugin: Creates submission.xml
3. User: Open eSTAR PDF in Acrobat
4. User: File → Import Data → submission.xml
5. User: Click Section 15 attachment icon
6. User: Browse to Bench_Test_Report.pdf
7. User: Click Section 12 attachment icon
8. User: Browse to ISO_10993_Report.pdf
9. ... (repeat for 10-20 files)
10. User: Save PDF
```

### With MCP Integration (Automated):
```
1. User: /fda:assemble --project X --attach-mode auto
2. Plugin: Generates eSTAR XML
3. Plugin: Generates attachment manifest
4. Plugin: Calls MCP server → opens PDF in Acrobat
5. Plugin: Imports XML data
6. Plugin: Batch attaches all files from manifest
7. Plugin: Saves PDF
8. Plugin: Reports "Submission package ready: submission.pdf (23 attachments)"
```

**Time savings: 30 min → 2 min**

---

## Code Example: MCP Server Implementation

### `mcp-servers/adobe-acrobat/index.js` (Node.js)

```javascript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { execSync, exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';

const execAsync = promisify(exec);

class AdobeAcrobatServer {
  constructor() {
    this.server = new Server(
      {
        name: 'adobe-acrobat',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();

    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler('tools/list', async () => ({
      tools: [
        {
          name: 'acrobat_open_pdf',
          description: 'Open a PDF file in Adobe Acrobat',
          inputSchema: {
            type: 'object',
            properties: {
              pdf_path: {
                type: 'string',
                description: 'Absolute path to PDF file',
              },
            },
            required: ['pdf_path'],
          },
        },
        {
          name: 'acrobat_attach_file',
          description: 'Attach a file to a specific section in an eSTAR PDF',
          inputSchema: {
            type: 'object',
            properties: {
              pdf_path: {
                type: 'string',
                description: 'Path to eSTAR PDF',
              },
              attachment_path: {
                type: 'string',
                description: 'Path to file to attach',
              },
              section: {
                type: 'string',
                description: 'eSTAR section number (e.g., "15" for Performance Testing)',
              },
              attachment_name: {
                type: 'string',
                description: 'Display name for attachment',
              },
            },
            required: ['pdf_path', 'attachment_path', 'section'],
          },
        },
        {
          name: 'acrobat_batch_attach',
          description: 'Attach multiple files from a manifest',
          inputSchema: {
            type: 'object',
            properties: {
              pdf_path: {
                type: 'string',
                description: 'Path to eSTAR PDF',
              },
              manifest: {
                type: 'object',
                description: 'JSON mapping {section → [file_paths]}',
              },
            },
            required: ['pdf_path', 'manifest'],
          },
        },
      ],
    }));

    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'acrobat_open_pdf':
            return await this.openPDF(args.pdf_path);

          case 'acrobat_attach_file':
            return await this.attachFile(
              args.pdf_path,
              args.attachment_path,
              args.section,
              args.attachment_name
            );

          case 'acrobat_batch_attach':
            return await this.batchAttach(args.pdf_path, args.manifest);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async openPDF(pdfPath) {
    const platform = process.platform;

    if (platform === 'darwin') {
      // macOS: Use AppleScript
      const script = `
        tell application "Adobe Acrobat"
          activate
          open POSIX file "${pdfPath}"
        end tell
      `;
      await execAsync(`osascript -e '${script}'`);
    } else if (platform === 'win32') {
      // Windows: Use start command
      await execAsync(`start "" "${pdfPath}"`);
    } else {
      throw new Error('Unsupported platform');
    }

    return {
      content: [
        {
          type: 'text',
          text: `Opened ${path.basename(pdfPath)} in Adobe Acrobat`,
        },
      ],
    };
  }

  async attachFile(pdfPath, attachmentPath, section, attachmentName) {
    // Validate files exist
    if (!fs.existsSync(pdfPath)) {
      throw new Error(`PDF not found: ${pdfPath}`);
    }
    if (!fs.existsSync(attachmentPath)) {
      throw new Error(`Attachment not found: ${attachmentPath}`);
    }

    // Section → page mapping for nIVD eSTAR v6.1
    const sectionPages = {
      '12': { page: 38, name: 'Biocompatibility' },
      '13': { page: 41, name: 'Software' },
      '14': { page: 43, name: 'EMC/Electrical' },
      '15': { page: 45, name: 'Performance Testing' },
      '16': { page: 48, name: 'Clinical' },
      '17': { page: 50, name: 'Human Factors' },
    };

    const sectionInfo = sectionPages[section];
    if (!sectionInfo) {
      throw new Error(`Unknown section: ${section}`);
    }

    const displayName = attachmentName || path.basename(attachmentPath);

    // Execute Acrobat JavaScript via AppleScript (macOS)
    const jsCode = `
var doc = this;
doc.importDataObject({
  cName: "${displayName}",
  cDIPath: "${attachmentPath}"
});
app.alert("Attached: ${displayName} to Section ${section}", 3);
    `.trim();

    const script = `
      tell application "Adobe Acrobat"
        activate
        tell active doc
          do script "${jsCode.replace(/"/g, '\\"')}"
        end tell
      end tell
    `;

    await execAsync(`osascript -e '${script}'`);

    return {
      content: [
        {
          type: 'text',
          text: `✓ Attached ${displayName} to Section ${section} (${sectionInfo.name})`,
        },
      ],
    };
  }

  async batchAttach(pdfPath, manifest) {
    const results = [];

    for (const [section, files] of Object.entries(manifest)) {
      for (const filePath of files) {
        try {
          const result = await this.attachFile(pdfPath, filePath, section);
          results.push(result.content[0].text);
        } catch (error) {
          results.push(`✗ Failed to attach ${filePath}: ${error.message}`);
        }
      }
    }

    return {
      content: [
        {
          type: 'text',
          text: results.join('\n'),
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Adobe Acrobat MCP server running on stdio');
  }
}

const server = new AdobeAcrobatServer();
server.run().catch(console.error);
```

---

## Configuration in Plugin

### `.mcp.json`

```json
{
  "mcpServers": {
    "adobe-acrobat": {
      "command": "node",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/mcp-servers/adobe-acrobat/index.js"
      ],
      "env": {
        "ACROBAT_PATH_MAC": "/Applications/Adobe Acrobat DC/Adobe Acrobat.app",
        "ACROBAT_PATH_WIN": "C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat\\Acrobat.exe"
      }
    }
  }
}
```

---

## Testing Plan

### Manual Testing
1. Create test eSTAR PDF with empty attachment fields
2. Prepare 3-5 test PDFs for attachment
3. Test each MCP tool individually
4. Test batch attachment
5. Verify attachments open correctly in Acrobat

### Automated Testing
```javascript
// test/adobe-acrobat-mcp.test.js
describe('Adobe Acrobat MCP Server', () => {
  it('should open a PDF', async () => {
    const result = await mcp.call('acrobat_open_pdf', {
      pdf_path: '/tmp/test.pdf'
    });
    expect(result.content[0].text).toContain('Opened');
  });

  it('should attach a file to Section 15', async () => {
    const result = await mcp.call('acrobat_attach_file', {
      pdf_path: '/tmp/estar.pdf',
      attachment_path: '/tmp/test_report.pdf',
      section: '15',
      attachment_name: 'Performance Test Report'
    });
    expect(result.content[0].text).toContain('Section 15');
  });
});
```

---

## Fallback for Non-Acrobat Users

If Adobe Acrobat is not installed, provide clear instructions:

```
⚠ Adobe Acrobat is required for automatic attachment.

Options:
1. Install Adobe Acrobat DC (free trial: https://acrobat.adobe.com/us/en/free-trial-download.html)
2. Manually attach files:
   - Open submission.pdf in Acrobat
   - Navigate to each section
   - Click the paperclip icon
   - Select the file from the list below

Attachment Checklist:
  Section 15 (Performance Testing):
    ☐ /path/to/Bench_Test_Report.pdf
    ☐ /path/to/Fatigue_Test_Report.pdf

  Section 12 (Biocompatibility):
    ☐ /path/to/ISO_10993_Report.pdf
```

---

## Next Steps

1. **Prototype the MCP server** (1-2 days)
2. **Test on macOS first** (easier with AppleScript)
3. **Add Windows COM support** (1 day)
4. **Integrate with `/fda:assemble` command** (2 days)
5. **User testing and refinement** (3-4 days)

**Total estimated effort: 1-2 weeks for full implementation**

---

## Benefits

- **70-80% time reduction** for eSTAR attachment step
- **Zero errors** from wrong file selection
- **Audit trail** of what was attached where
- **Reusable** for future submissions (save manifest template)
- **Extendable** to other PDF form workflows beyond FDA

---

## Alternative: Browser-Based eSTAR Portal Integration

If FDA releases a browser-based eSTAR submission portal (future), we could alternatively:
- Use **Playwright MCP server** (already exists in this plugin!)
- Automate form filling + attachment upload via browser
- No Acrobat dependency

This would be the long-term solution once FDA modernizes their submission system.
