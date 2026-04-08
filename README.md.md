# File Processing Project - DataCamp Practice

## Exercise Overview
Learning JSON file parsing and automated documentation generation.

## Files
- `file_processor.py` - Main script for processing JSON/SLP files
- `json_parser.py` - JSON parsing utilities  
- `diagram_generator.py` - Workflow diagram creation
- `../practice_data/sample_workflow.slp` - Sample data for testing

## Learning Objectives
- Parse complex JSON file structures
- Extract structured data from nested objects
- Generate visual workflow diagrams
- Automate documentation creation
- Practice file I/O and error handling

## Usage Examples

### Basic Processing
```bash
python file_processor.py ../practice_data/sample_workflow.slp
```

### Generate Summary Only
```bash
python file_processor.py ../practice_data/sample_workflow.slp --summary
```

### Generate Diagram Only  
```bash
python file_processor.py ../practice_data/sample_workflow.slp --diagram
```

### Save to File
```bash
python file_processor.py ../practice_data/sample_workflow.slp output.md
```

## Skills Practiced
- JSON parsing with error handling
- Object-oriented programming (classes)
- File I/O operations
- Data structure manipulation
- Documentation generation
- Command-line interfaces

---
*DataCamp "Working with Files in Python" - Personal practice exercises*
