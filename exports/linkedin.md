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
Senior Full Stack Software Engineer and designated technical lead for AI-driven engineering acceleration, with 7+ years building production systems across .NET, Python, Vue, and AWS. At Morningstar, architected the team's AI-assisted engineering harness, worked with MCP (Model Context Protocol) servers, and owned an LLM-driven audio feature using Amazon Bedrock and Polly. Owns delivery end to end across distributed systems, REST and GraphQL APIs, Harness CI/CD, and cloud infrastructure.
```
  <!-- 491 / 2600 chars - OK -->

## Experience

### Full Stack Software Engineer - Morningstar

Toronto, Canada | 2025-01 to Present

```
- Designated lead for AI-driven engineering acceleration: architected the team's AI-assisted engineering harness (skill files, scoped context and token budgets, operating-mode guardrails) and mentored senior and principal engineers onto it as their default workflow.
- Technical SME for MCP (Model Context Protocol) server architecture, from proposal through production release.
- Owned end-to-end delivery of an AI audio feature: .NET services on AWS Bedrock and Polly for LLM-driven SSML synthesis, plus the Vue UI shipping transcript and smart-summary output.
- Built a GraphQL API over a knowledge graph, improving content discoverability across the platform.
- Designed Harness CI/CD pipelines in YAML for AWS Lambda and ECS deploys, cutting deployment time.
- Built an automated Playwright test suite covering smoke, unit, and integration tests.
```
  <!-- 851 / 2000 chars - OK -->

### Software Engineer - Santoku Corporation / Rimm.ai

Toronto, Canada | 2019-08 to 2025-01

```
- Led the rearchitecture of a monolithic on-premises application into AWS microservices on Docker and Kubernetes.
- Owned custom haptic VR training systems for enterprise clients end-to-end as primary technical decision-maker.
```
  <!-- 226 / 2000 chars - OK -->

### English Language Teacher - Japan Exchange Teaching (JET) Program

Tokyo, Japan | 2018-08 to 2019-08

```
- Taught 1,000+ elementary and 500 middle school students, adapting curriculum using self-taught Japanese (JLPT N2).
```
  <!-- 116 / 2000 chars - OK -->

## Skills

LinkedIn allows 50 skills. Add in this order - the first three show on your profile.

1. LLM Orchestration
2. Bedrock
3. MCP
4. Agentic Harnesses
5. Prompt Engineering
6. Answer Engine Optimization
7. SEO
8. Python
9. Go
10. Java
11. C#
12. TypeScript
13. JavaScript
14. SQL
15. PowerShell
16. Bash
17. Gremlin
18. Microservices
19. Distributed Systems
20. REST
21. GraphQL
22. .NET
23. Spring Boot
24. Vue 3
25. Test Automation
26. Tableau
27. Graph Databases
28. AWS
29. GCP
30. Docker
31. Kubernetes
32. Terraform
33. CI/CD
34. IaC

## Licenses & certifications

- **AWS Certified Machine Learning Engineer - Associate** - AWS Training and Certification, issued 2026
- **AWS Certified AI Practitioner** - AWS Training and Certification, issued 2025
- **Google Cloud Certified: Professional Cloud Architect** - Google Cloud Certification, issued 2024
- **AWS Certified Solutions Architect - Professional** - AWS Training and Certification, issued 2023

## Education

- **McMaster University** - Bachelor of Honors Science - Kinesiology
  - Hamilton, Canada | 2014-09 to 2018-04

## Projects

- **Agentic Engineering Harness** (https://github.com/Freddy-S3/agent-agnostic-harness)
  - Provider-neutral harness for autonomous coding agents across Copilot, Claude Code, and Codex: operating modes for supervised vs. unattended posture, plus a usage-limit-aware queue that resumes after rate-limit resets.
- **The Compounding Engineer** (https://github.com/Freddy-S3/unattended-runs)
  - SEO- and ad-monetized technical blog on Astro covering agentic harness engineering and self-directed learning.
- **Portfolio Site & Resume Pipeline** (https://freddyshaikh.com)
  - Single-source-of-truth pipeline: Python generators cascade one LaTeX source into the site, the PDF, and ATS / JSON Resume / LinkedIn exports, CI-verified with Playwright.
