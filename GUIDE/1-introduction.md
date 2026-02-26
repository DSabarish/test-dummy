# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Terraform + CI/CD: Infrastructure as Code for ML/AI/Data Projects

> **Document Type:** Internal Engineering Reference  
> **Audience:** Engineers new to Infrastructure as Code (beginner → intermediate)  
> **Status:** 🟢 Active Template — Reusable across all DataNeurus projects  
> **Last Updated:** 2025

---

## Table of Contents

1. [Introduction](1-introduction.md)
2. [Why Terraform Instead of Python + GCP SDK](2-why-terraform-python-gcp-sdk.md)
3. [Responsibility Split: Terraform vs CI/CD](3-responsibility-split-terraform-cicd.md)
4. [Terraform Project Structure](4-terraform-project-structure.md)
5. [Terraform Code Walkthrough](5-terraform-code-walkthrough.md)
6. [Terraform Workflow](6-terraform-workflow.md)
7. [CI/CD Integration](7-cicd-integration.md)
8. [Maintenance & Scaling](8-maintenance-scaling.md)
9. [Quick Reference Cheatsheet](9-quick-reference-cheatsheet.md)

---

**Part 1 · Introduction** · [← Index](README.md)

---

## 1. Introduction

### 1.1 What is CI/CD?

**CI/CD** stands for **Continuous Integration / Continuous Delivery (or Deployment)**. It is a set of practices and tools that automate the software lifecycle — from writing code to testing it, to deploying it to production.

```
Developer writes code
        │
        ▼
┌───────────────────┐
│  Push to GitHub   │  ◄── Triggers the CI/CD pipeline automatically
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  CI: Test & Build │  ◄── Run tests, lint, validate
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  CD: Deploy       │  ◄── Push to Cloud Run, update containers, etc.
└───────────────────┘
        │
        ▼
    ✅ Live in production
```

Think of CI/CD as a **robot colleague** that automatically checks your work and deploys it every time you push code — removing the need for manual, error-prone steps.

---

### 1.2 Why CI/CD is Important for ML/AI/Data Projects

ML/AI/Data projects are uniquely complex. Unlike a traditional web app, they involve:

- **Data pipelines** that pull from multiple sources
- **Model training** runs that depend on GCS buckets, BigQuery datasets, and service accounts existing *before* the code runs
- **Multiple environments** — dev, qa, and prod — each with different projects, permissions, and resources
- **Frequent iteration** — data scientists push code daily; infrastructure must keep up

> ⚠️ **Without CI/CD**, every model update or pipeline change requires:
> - Manual SSH into a server
> - Running scripts by hand
> - Hoping nothing was forgotten
> - Praying the environment is the same as last week

CI/CD solves this by making deployments **repeatable, automated, and auditable**. Every change is tracked in Git, every deploy is logged, and every failure is caught early.

---

### 1.3 Common Problems When Using CI/CD Alone

CI/CD is excellent at automating *application* deployment — but it was not designed to manage *infrastructure*. When teams try to use CI/CD alone (without a tool like Terraform), they hit a familiar set of problems:

#### ❌ Problem 1: Manual Infrastructure Creation

```
Engineer A: "I'll just create the BigQuery dataset manually in the console."
Engineer B (3 months later): "Wait, why does prod have a dataset called 'training_v2_old'?"
```

Manually created resources are not tracked anywhere. They exist in the cloud but not in code.

#### ❌ Problem 2: Configuration Drift

Drift happens when the **actual state** of your infrastructure slowly diverges from the **expected state**. Example:

- You intended `dev` and `prod` to have identical bucket configurations
- Someone adds a lifecycle rule to `prod` via the console
- Now `dev` and `prod` are different — but nobody knows
- A bug appears in `prod` that doesn't happen in `dev`

Drift is **silent and cumulative**. It builds up over months until something breaks.

#### ❌ Problem 3: Reproducibility Issues

> "It works on my machine (and in dev). I have no idea why prod is broken."

If infrastructure was created by hand, spinning up a new environment means following a checklist — and checklists drift too. You may forget a permission, a bucket, or a BigQuery table schema. The new environment is never *exactly* like the original.

#### ❌ Problem 4: No Audit Trail

Who created that service account? When was that IAM role added? Why does `qa` have admin permissions? If infrastructure is managed manually, **there is no history**. With Terraform, every infrastructure change is a Git commit.

#### ❌ Problem 5: Onboarding New Projects is Slow

Starting a new ML project means:
1. Manually creating a GCP project
2. Enabling APIs one by one
3. Creating buckets, datasets, service accounts
4. Writing down the steps (probably imperfectly)
5. Repeating for dev, qa, prod

This takes days. With Terraform, it takes minutes.

---

### 1.4 How Terraform Complements CI/CD

Terraform fills the gap that CI/CD leaves open: **infrastructure management**.

```

├─────────────────────────────┬───────────────────────────────┤
│         TERRAFORM           │           CI/CD               │
│   "Build the foundation"    │   "Deploy what runs on it"    │
├─────────────────────────────┼───────────────────────────────┤
│  • GCS Buckets              │  • Run ML pipeline            │
│  • BigQuery datasets/tables │  • Build Docker image         │
│  • Artifact Registry        │  • Deploy to Cloud Run        │
│  • Service Accounts + IAM   │  • Run tests                  │
│  • APIs enabled             │  • Promote dev → qa → prod    │
└─────────────────────────────┴───────────────────────────────┘
```

Together, they form a **complete, automated system** where:

1. **Terraform** creates and maintains the cloud infrastructure
2. **Terraform outputs** (non-secret values like bucket names, project IDs) are passed to CI/CD
3. **CI/CD** uses those values to run pipelines and deployments

> 💡 **The key insight:** Terraform is *not* a replacement for CI/CD. It is the layer underneath it. CI/CD deploys *applications*. Terraform manages the *infrastructure those applications run on*.

---

[← Index](README.md) · [Next: Why Terraform Instead of Python + GCP SDK →](2-why-terraform-python-gcp-sdk.md)
