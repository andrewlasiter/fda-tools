# Backup and Recovery Procedures

**System:** FDA OpenFDA Offline Database  
**Version:** 1.0  
**Last Updated:** 2026-02-20  
**Regulatory Basis:** 21 CFR Part 11.10(b) - Data Copy Generation

## 1. Overview

This document defines backup and recovery procedures for the PostgreSQL Offline Database to ensure:
- **Data availability:** 99.9% uptime with <15 minute RTO
- **Data durability:** 7-year retention per regulatory requirements
- **Data integrity:** GPG encryption and checksum verification
- **Disaster recovery:** Point-in-time recovery with <5 minute RPO

## 2. Backup Strategy

### 2.1 Backup Types

| Type | Method | Frequency | Retention | Purpose |
|------|--------|-----------|-----------|---------|
| **Full Backup** | pg_dump -Fc | Daily (2 AM) | 7 days | Complete database snapshot |
| **Weekly Backup** | pg_dump -Fc | Sunday 2 AM | 4 weeks | Weekly checkpoint |
| **Monthly Backup** | pg_dump -Fc | 1st of month | 12 months | Monthly archive |
| **Yearly Backup** | pg_dump -Fc | Jan 1st | 7 years | Regulatory compliance |
| **WAL Archiving** | pg_basebackup | Continuous | 14 days | Point-in-time recovery |

### 2.2 Backup Schedule (Cron Format)

Daily full backup at 2 AM: 0 2 * * *

WAL archiving runs continuously via PostgreSQL archive_command.

### 2.3 Retention Policy

**Regulatory Requirement:** 21 CFR Part 11.10(b) requires ability to generate accurate copies for regulatory inspection.

**Implementation:**
- Daily: 7 days (8 total backups including current)
- Weekly: 4 weeks (4 Sunday backups)
- Monthly: 12 months (12 backups on 1st of month)
- Yearly: 7 years (7 backups on January 1st)

**Total Storage:** ~2.5 years of data coverage with compliance retention

## 3. Security & Compliance

See CFR_PART_11_COMPLIANCE.md and SYSTEM_VALIDATION.md for complete compliance documentation.

**Key Controls:**
- ✅ GPG encryption (RSA 4096)
- ✅ 7-year retention policy
- ✅ Automated verification
- ✅ Point-in-time recovery (RPO <5 minutes)
- ✅ Full restore capability (RTO <15 minutes)

## 4. Recovery Procedures

### 4.1 Full Database Recovery

**RTO:** <15 minutes  
**RPO:** Last full backup (up to 24 hours)

See backup_manager.py for complete restore procedures.

### 4.2 Point-in-Time Recovery

**RTO:** <15 minutes  
**RPO:** <5 minutes (WAL archiving interval)

Uses PostgreSQL WAL replay to recover to specific timestamp.

### 4.3 Blue-Green Rollback

**RTO:** <10 seconds  
**RPO:** 0 (BLUE database unchanged)

Instant rollback via PgBouncer configuration switch.

## 5. Monitoring & Alerts

**Backup Success:**
- CRITICAL: Backup failed 2 consecutive days
- HIGH: Backup duration >30 minutes
- MEDIUM: Backup size anomaly (±50% variance)

**Storage:**
- CRITICAL: Disk usage >90%
- HIGH: S3 bucket size >1 TB

## 6. Compliance

**Regulatory Requirements:**
- ✅ 21 CFR Part 11.10(b): Data copy generation
- ✅ 7-year retention: Regulatory record retention
- ✅ Encryption: GPG for backup security
- ✅ Verification: Automated integrity validation

---

**Document Control:**  
Version: 1.0  
Approved By: [Pending stakeholder approval]  
Next Review: 2027-02-20
