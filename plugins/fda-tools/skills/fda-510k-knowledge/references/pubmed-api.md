# PubMed E-utilities API Reference

## Overview

NCBI E-utilities provide programmatic access to PubMed for structured, reproducible literature searches. Unlike web search, E-utilities return structured data with PMIDs, MeSH terms, and citation counts.

**Base URL:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`

## Endpoints

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `esearch.fcgi` | Search PubMed, return PMIDs | `/fda:literature` — primary search |
| `efetch.fcgi` | Retrieve article details (title, abstract, authors) | `/fda:literature` — article details |
| `elink.fcgi` | Find related articles, citation counts | `/fda:literature --depth deep` |
| `einfo.fcgi` | Database metadata | Diagnostic only |

## Rate Limiting

| Condition | Rate Limit |
|-----------|-----------|
| Without API key | 3 requests/second |
| With API key | 10 requests/second |
| Tool/email identification | Required for all requests |

**API key configuration:**
- **Priority 1:** Environment variable `NCBI_API_KEY`
- **Priority 2:** Settings file `~/.claude/fda-predicate-assistant.local.md` field `ncbi_api_key`
- **Obtain key:** Register at [NCBI](https://www.ncbi.nlm.nih.gov/account/) — free

Configure via: `/fda:configure --set ncbi_api_key YOUR_KEY`

## esearch — PubMed Search

```
GET esearch.fcgi?db=pubmed&term={query}&retmax=20&retmode=json&sort=relevance&tool=fda-predicate-assistant&email=plugin@example.com
```

**Parameters:**
- `db=pubmed` — Database
- `term` — Search query (supports PubMed query syntax)
- `retmax` — Maximum results (default 20, max 10000)
- `retmode=json` — Return format
- `sort=relevance` — Sort order (relevance, pub_date)
- `api_key` — Optional NCBI API key

**Response:**
```json
{
  "esearchresult": {
    "count": "142",
    "retmax": "20",
    "idlist": ["38123456", "37654321", ...]
  }
}
```

## efetch — Retrieve Article Details

```
GET efetch.fcgi?db=pubmed&id={pmid1,pmid2,...}&rettype=abstract&retmode=xml&tool=fda-predicate-assistant&email=plugin@example.com
```

**Parameters:**
- `db=pubmed` — Database
- `id` — Comma-separated PMIDs (max 200 per request)
- `rettype=abstract` — Return type (abstract, medline, full)
- `retmode=xml` — Return format (xml recommended for structured parsing)
- `api_key` — Optional NCBI API key

**Response XML structure** (key fields for parsing):

```xml
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>38123456</PMID>
      <Article>
        <Journal>
          <Title>Journal of Medical Devices</Title>
          <JournalIssue>
            <Volume>18</Volume>
            <Issue>3</Issue>
            <PubDate><Year>2024</Year><Month>Sep</Month></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Clinical outcomes of device X...</ArticleTitle>
        <Abstract>
          <AbstractText>BACKGROUND: ... METHODS: ... RESULTS: ... CONCLUSIONS: ...</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>JD</Initials></Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Clinical Trial</PublicationType>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName MajorTopicYN="Y">Prostheses and Implants</DescriptorName>
        </MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
```

**Key XML paths for parsing:**

| Field | XPath | Description |
|-------|-------|-------------|
| PMID | `.//PMID` | PubMed unique identifier |
| Title | `.//ArticleTitle` | Article title text |
| Journal | `.//Journal/Title` | Journal name |
| Year | `.//PubDate/Year` | Publication year |
| Abstract | `.//AbstractText` | Full abstract text |
| Authors | `.//Author/LastName` + `.//Author/Initials` | Author names |
| Pub Type | `.//PublicationType` | Publication type(s) — multiple possible |
| MeSH | `.//DescriptorName` | MeSH heading terms |
| DOI | `.//ArticleId[@IdType="doi"]` | DOI identifier |
| Volume | `.//Volume` | Journal volume |
| Issue | `.//Issue` | Journal issue |

**Publication types relevant to FDA literature review:**

| Publication Type | Evidence Level | Use Case |
|-----------------|---------------|----------|
| `Randomized Controlled Trial` | Highest | Pivotal clinical evidence |
| `Clinical Trial` | High | Clinical performance data |
| `Meta-Analysis` | High | Aggregate evidence |
| `Systematic Review` | High | Comprehensive evidence synthesis |
| `Comparative Study` | Moderate | Device comparison data |
| `Observational Study` | Moderate | Real-world safety data |
| `Case Reports` | Low | Adverse event signal detection |
| `Review` | Varies | Background and context |
| `Validation Study` | Moderate | Test method validation |

## elink — Related Articles and Citation Counts

```
GET elink.fcgi?dbfrom=pubmed&id={pmid}&cmd=neighbor_score&tool=fda-predicate-assistant&email=plugin@example.com
```

**Parameters:**
- `dbfrom=pubmed` — Source database
- `id` — PMID(s) to find related articles for
- `cmd=neighbor_score` — Return related articles with relevance scores
- `linkname=pubmed_pubmed_citedin` — Find articles that cite this one (citation count)

**Use cases:**
- Find related studies for a key article
- Count citations to assess article impact
- Discover additional relevant literature from citation networks

## MeSH Term Mapping for Medical Devices

Use MeSH terms to improve search precision. Common mappings for device categories:

| Device Category | MeSH Terms |
|----------------|------------|
| Orthopedic implants | "Bone Screws"[MeSH], "Spinal Fusion"[MeSH], "Internal Fixators"[MeSH] |
| Cardiovascular | "Stents"[MeSH], "Heart Valve Prosthesis"[MeSH], "Balloon Dilatation"[MeSH] |
| Software/SaMD | "Software"[MeSH], "Artificial Intelligence"[MeSH], "Image Processing, Computer-Assisted"[MeSH] |
| Wound care | "Bandages"[MeSH], "Wound Healing"[MeSH], "Occlusive Dressings"[MeSH] |
| Dental | "Dental Implants"[MeSH], "Orthodontic Brackets"[MeSH], "Dental Prosthesis"[MeSH] |
| IVD/diagnostics | "Clinical Laboratory Techniques"[MeSH], "Biosensing Techniques"[MeSH] |
| Ophthalmic | "Lenses, Intraocular"[MeSH], "Contact Lenses"[MeSH], "Ophthalmoscopes"[MeSH] |
| Respiratory | "Ventilators, Mechanical"[MeSH], "Respiratory Protective Devices"[MeSH] |
| Infusion | "Infusion Pumps"[MeSH], "Drug Delivery Systems"[MeSH] |

## PubMed Query Syntax

### Field Tags
- `[Title/Abstract]` — Search title and abstract
- `[MeSH Terms]` — Search MeSH index
- `[Publication Type]` — Filter by type (e.g., "Clinical Trial", "Review", "Meta-Analysis")
- `[Title]` — Title only

### Boolean Operators
- `AND`, `OR`, `NOT` — Standard boolean
- Parentheses for grouping

### Filters
- `"clinical trial"[Publication Type]` — Clinical trials only
- `"review"[Publication Type]` — Reviews only
- `"last 5 years"[PDat]` — Date filter (relative)
- `"2020/01/01"[PDat]:"2025/12/31"[PDat]` — Date range (absolute)
- `"humans"[MeSH]` — Human studies only (excludes animal studies)
- `"english"[Language]` — English language only
- `"free full text"[Filter]` — Only articles with free full text

### Common Filter Combinations for 510(k) Reviews

**High-quality clinical evidence only:**
```
({device_terms}) AND ("clinical trial"[Publication Type] OR "randomized controlled trial"[Publication Type]) AND "humans"[MeSH] AND "last 10 years"[PDat]
```

**Safety signals (broad):**
```
({device_terms}) AND (adverse[Title/Abstract] OR complication[Title/Abstract] OR failure[Title/Abstract] OR recall[Title/Abstract]) AND "last 10 years"[PDat]
```

**Systematic reviews and meta-analyses (highest evidence):**
```
({device_terms}) AND ("systematic review"[Publication Type] OR "meta-analysis"[Publication Type])
```

**Standards and testing methodology:**
```
({device_terms}) AND ("ISO"[Title/Abstract] OR "ASTM"[Title/Abstract] OR "IEC"[Title/Abstract]) AND (testing[Title/Abstract] OR validation[Title/Abstract])
```

### Example Queries for FDA Literature Review

**Clinical evidence for a specific device:**
```
("{device_name}"[Title/Abstract]) AND (clinical trial[Publication Type] OR clinical study[Title/Abstract])
```

**Safety/adverse events:**
```
("{device_name}"[Title/Abstract]) AND (adverse event[Title/Abstract] OR complication[Title/Abstract] OR safety[Title/Abstract])
```

**Biocompatibility:**
```
("{device_name}"[Title/Abstract]) AND (biocompatibility[Title/Abstract] OR cytotoxicity[Title/Abstract] OR "ISO 10993"[Title/Abstract])
```

**Systematic reviews (highest evidence):**
```
("{device_name}"[Title/Abstract]) AND (systematic review[Publication Type] OR meta-analysis[Publication Type])
```

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| HTTP 429 | Rate limit exceeded | Wait 1 second, retry; add API key for higher limits |
| HTTP 502/503 | NCBI server issue | Retry after 5 seconds; fall back to WebSearch |
| Empty result | No matching articles | Broaden search terms; try MeSH terms; fall back to WebSearch |
| Timeout | Slow response | Retry with smaller retmax; check network |
