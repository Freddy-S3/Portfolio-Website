# LinkedIn paste sheet

Generated from `resume/resume/*.tex`. Do not edit by hand - rerun `py tools/resume_export.py`.
Character counts against LinkedIn's limits are noted inline.

## Headline

```
Senior Full Stack Software Engineer
```
  <!-- 35 / 220 chars - OK -->

## About

```
Senior Full Stack Software Engineer with 7+ years delivering cloud-native systems on AWS and turning emerging AI capabilities into reliable engineering practice. At Morningstar, I lead end-to-end AI product delivery and built the team's AI-assisted engineering harness: skill files, scoped context, and token budgets that make agentic workflows repeatable. Self-taught in programming, Japanese, and French, I translate current AI research into practical team capability.
```
  <!-- 470 / 2600 chars - OK -->

## Experience

### Full Stack Software Engineer - Morningstar

Toronto, Canada | 2025-01 to Present

```
- Serving as the designated lead for AI-driven engineering acceleration: pioneered the team's AI-assisted engineering harness (skill files, scoped context/token budgets, operating-mode guardrails) and mentored senior and principal engineers onto it as their default workflow.
- Led MCP (Model Context Protocol) server architecture as technical SME, from proposal through production release.
- Owned end-to-end delivery of an AI audio feature: .NET services on AWS Bedrock/Polly for LLM-driven SSML synthesis, plus the Vue UI shipping transcript and smart-summary formats.
- Designed and deployed Harness CI/CD pipelines with Infrastructure as Code, reducing AWS Lambda and ECS deployment time by 80%.
- Coded Python scripts for process automation to reduce repetitive tasks by 75%.
```
  <!-- 781 / 2000 chars - OK -->

### Software Engineer - Santoku Corporation / Rimm.ai

Toronto, Canada | 2019-08 to 2025-01

```
- Led the rearchitecture of a monolithic on-premises app into AWS cloud microservices for independent deployability and uptime.
- Containerized the application with Docker and orchestrated it with Kubernetes for a 75% decrease in downtime.
- Owned custom haptic VR training systems for enterprise clients end-to-end as primary technical decision-maker, from requirements through delivery.
```
  <!-- 388 / 2000 chars - OK -->

### English Language Teacher - Japan Exchange Teaching (JET) Program

Tokyo, Japan | 2018-08 to 2019-08

```
- Delivered English instruction to over 1,000 elementary and 500 middle school students, adapting curriculum using self-taught Japanese.
```
  <!-- 136 / 2000 chars - OK -->

## Skills

LinkedIn allows 50 skills. Add in this order - the first three show on your profile.

1. Python
2. Go
3. Java
4. JavaScript
5. TypeScript
6. C#
7. SQL
8. Bash
9. PowerShell
10. VBA
11. Gremlin
12. HTML
13. CSS
14. AWS
15. GCP
16. Kafka
17. Docker
18. Kubernetes
19. Terraform
20. .NET
21. Vue
22. Git
23. AI-Assisted Harnesses
24. MCP
25. Agentic Orchestration
26. Prompt Engineering

## Licenses & certifications

- **Google Cloud Certified: Professional Cloud Architect** - Google Cloud Certification, issued 2024
- **AWS Certified Machine Learning Engineer - Associate** - AWS Training and Certification, issued 2026
- **AWS Certified AI Practitioner** - AWS Training and Certification, issued 2025
- **AWS Certified Solutions Architect - Professional** - AWS Training and Certification, issued 2023

## Projects

- **Agentic Engineering Harness** (https://github.com/Freddy-S3/claude-harness-public)
  - Designed a provider-neutral harness for autonomous coding agents: operating modes for supervised vs. unattended posture, a recoverability-over-approval model for overnight runs, and a usage-limit-aware queue that resumes work after rate-limit resets.
- **The Compounding Engineer** (https://github.com/Freddy-S3/unattended-runs)
  - Built and write an SEO- and ad-monetized technical blog (Astro, content collections, RSS/sitemap/OpenGraph, AdSense) covering agentic harness engineering and self-directed learning, with a tag-driven content pillar system and a documented prompt-to-article authoring workflow.
- **Portfolio Site & Resume Pipeline** (https://freddyshaikh.com)
  - Designed a single-source-of-truth pipeline: a Python generator cascades this LaTeX resume into the site (JavaScript, SCSS, AWS CloudFront), PDF, and job-board exports, eliminating manual re-sync, CI-verified with Playwright.
