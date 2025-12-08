# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-08

### Added
- Initial release of Slitlamp Image Labeling Application
- Multi-user authentication system with role-based access
- Image labeling interface with clinical context
- Smart clinical note matching (before/after exam date)
- Four route strategies for distributed labeling
- Label management with edit history and timestamps
- Review queue functionality
- Admin dashboard with comprehensive statistics
- User management interface
- Label review and filtering system
- CSV export functionality
- Progress tracking and visualization
- Automatic advance to next unlabeled image
- Skip and navigation controls

### Features
- **Laterality labeling**: Left/Right
- **Diagnosis options**: Ulcer, Hyposphagma, Dry Eye, Pterygium, Pinguecula, Other
- **Quality assessment**: Usable/Not Usable
- **Flagging system**: Yes/No
- **Clinical context**: Exam details and notes
- **Route strategies**: Forward, Backward, Middle-out, Random

### Security
- SHA-256 password hashing
- Session-based authentication
- Role-based access control (Admin/Labeler)

### Data Management
- JSON-based label storage
- Comprehensive metadata tracking
- Edit history preservation
- User-specific label files

## [Future Releases]

### Planned Features
- [ ] Batch export of all labels
- [ ] Label comparison between users
- [ ] Inter-rater agreement calculations
- [ ] Image annotation tools (draw on images)
- [ ] Keyboard shortcuts for faster labeling
- [ ] Label conflicts resolution interface
- [ ] Advanced search and filtering
- [ ] Backup and restore functionality
- [ ] API for external integrations
- [ ] Mobile-responsive design improvements

### Under Consideration
- DICOM support
- Integration with PACS systems
- Machine learning model integration for pre-labeling
- Collaborative labeling with real-time updates
- Advanced image preprocessing tools
