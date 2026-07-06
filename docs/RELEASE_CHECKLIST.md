# Git Standup Bot v1.0.0 Release Checklist

This checklist tracks the release readiness tasks for version `v1.0.0`.

### Source and Git
- [x] main is synchronized with origin/main
- [ ] working tree is clean
- [ ] no secrets or generated files
- [ ] release documentation merged to main
- [ ] release commit confirmed on main
- [ ] tag points to expected main commit

### Verification
- [x] pip check
- [x] 64 targeted tests
- [x] 127 full tests
- [x] CLI help
- [x] deterministic offline report
- [x] deterministic Standup Agent fallback
- [x] real Ollama Standup Agent test (verified offline execution on Windows via llama3.1:8b)
- [x] invalid provider error behavior
- [x] Markdown export
- [x] CP1254 output

### CI
- [x] Python 3.10 Ubuntu
- [x] Python 3.10 Windows
- [x] Python 3.11 Ubuntu
- [x] Python 3.11 Windows
- [x] Python 3.12 Ubuntu
- [x] Python 3.12 Windows
- [x] Python 3.13 Ubuntu
- [x] Python 3.13 Windows

### Release
- [ ] CHANGELOG Pending replaced with real date
- [ ] annotated tag `v1.0.0` created
- [ ] tag points to expected main commit
- [ ] GitHub Release created
- [ ] release notes published
- [ ] installation commands verified from the published release
- [ ] release assets checked
- [ ] repository topics/description finalized
