# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI-DLC Workflow Configuration

This project is configured with **AI-DLC (AWS AI Development Lifecycle) v1.0.1** workflows for enhanced code review and development assistance.

### Rule Details

The `.aidlc-rule-details/` directory contains detailed guidelines and standards for:
- **ascii-diagram-standards.md** — Standards for creating ASCII diagrams in documentation
- **content-validation.md** — Guidelines for validating content quality
- **depth-levels.md** — Standards for API/documentation depth levels
- **error-handling.md** — Best practices for error handling
- **overconfidence-prevention.md** — Techniques to prevent overconfident code assessments

These rules are used during code review and development to ensure consistency with AWS best practices.

### Claude Code Settings

The `.claude/settings.json` file contains the configuration for Claude Code integration, including PR attribution settings for contributions to this project.

## Project Status

This repository is currently in setup phase. When project files are committed, update this CLAUDE.md with:

1. **Build and Test Commands** — How to build, run tests (full suite and single tests), and lint code
2. **Architecture Overview** — High-level structure and key components
3. **Development Workflow** — Important conventions and patterns specific to this codebase
