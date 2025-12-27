#!/usr/bin/env python3
"""
PrepMate Standalone - Quick Repository Consolidator
Copy this file to any repo and run: python prepmate.py
Now respects .gitignore patterns!
"""

import os
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Optional, Pattern
from collections import defaultdict
import fnmatch

# Default file extensions to include
DEFAULT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx',  # Code
    '.md', '.txt', '.rst',                 # Documentation
    '.json', '.yaml', '.yml',              # Config
    '.html', '.css', '.scss',              # Web
    '.sol', '.cairo',                      # Blockchain
    '.go', '.rs', '.java', '.cpp', '.c',  # Additional languages
    '.h', '.hpp', '.cs', '.rb', '.php',   # More languages
    '.swift', '.kt', '.scala', '.r'       # Even more languages
}

# Special files to always include (regardless of extension)
SPECIAL_FILES = {
    'Dockerfile', 'Makefile', 'README', 'LICENSE',
    'requirements.txt', 'setup.py', 'setup.cfg',
    'pyproject.toml', 'Cargo.toml', 'go.mod',
    '.env.example', 'docker-compose.yml', 'docker-compose.yaml'
}

# Always exclude these, even if not in .gitignore
ALWAYS_EXCLUDE_DIRS = {
    '.git',  # Git repository data
}

ALWAYS_EXCLUDE_FILES = {
    'prepmate.py',  # Exclude PrepMate itself
    '.DS_Store', 'Thumbs.db',  # OS files
}


class GitignoreParser:
    """Parse and apply .gitignore patterns"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.patterns = []
        self.parse_gitignore()
    
    def parse_gitignore(self):
        """Parse .gitignore file if it exists"""
        gitignore_path = self.root_path / '.gitignore'
        
        if not gitignore_path.exists():
            print("📝 No .gitignore found, using minimal exclusions")
            return
        
        print(f"📝 Reading .gitignore patterns...")
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Store the pattern
                    self.patterns.append(line)
            
            print(f"   Found {len(self.patterns)} ignore patterns")
        except Exception as e:
            print(f"⚠️  Error reading .gitignore: {e}")
    
    def is_ignored(self, path: Path, is_dir: bool = False) -> bool:
        """Check if a path should be ignored based on gitignore patterns"""
        # Get relative path from root
        try:
            rel_path = path.relative_to(self.root_path)
        except ValueError:
            return False
        
        # Convert to string with forward slashes
        path_str = str(rel_path).replace(os.sep, '/')
        
        # Check each pattern
        for pattern in self.patterns:
            original_pattern = pattern
            negate = False
            
            # Handle negation patterns
            if pattern.startswith('!'):
                negate = True
                pattern = pattern[1:]
            
            # Handle directory-only patterns
            if pattern.endswith('/'):
                if not is_dir:
                    continue
                pattern = pattern[:-1]
            
            # Handle patterns that should match from root
            if pattern.startswith('/'):
                pattern = pattern[1:]
                # Pattern must match from the beginning
                if self._matches_pattern(path_str, pattern, anchored=True):
                    if negate:
                        return False
                    return True
            else:
                # Pattern can match anywhere in the path
                if self._matches_pattern(path_str, pattern, anchored=False):
                    if negate:
                        return False
                    return True
                
                # Also check if any parent directory matches
                parts = path_str.split('/')
                for i in range(len(parts)):
                    partial = '/'.join(parts[:i+1])
                    if self._matches_pattern(partial, pattern, anchored=False):
                        if negate:
                            return False
                        return True
        
        return False
    
    def _matches_pattern(self, path: str, pattern: str, anchored: bool = False) -> bool:
        """Check if a path matches a gitignore pattern"""
        # Handle ** wildcards
        pattern = pattern.replace('**/', '**')
        pattern = pattern.replace('/**', '**')
        
        # Convert gitignore pattern to regex
        regex_pattern = self._gitignore_to_regex(pattern)
        
        if anchored:
            # Must match from the beginning
            return re.match(regex_pattern, path) is not None
        else:
            # Can match anywhere
            if re.search(regex_pattern, path):
                return True
            # Also check if the pattern matches the basename
            basename = os.path.basename(path)
            if re.match(regex_pattern, basename):
                return True
        
        return False
    
    def _gitignore_to_regex(self, pattern: str) -> str:
        """Convert a gitignore pattern to a regex pattern"""
        # Escape special regex characters except * and ?
        pattern = re.escape(pattern)
        pattern = pattern.replace(r'\*', '.*')
        pattern = pattern.replace(r'\?', '.')
        pattern = pattern.replace(r'\*\*', '.*')
        
        return f'^{pattern}$'


class QuickPrepMate:
    """Simplified PrepMate for quick repository consolidation"""
    
    def __init__(self, root_path: str = ".", output_file: str = None, 
                 extensions: Set[str] = None, max_file_size: int = 1_000_000,
                 use_gitignore: bool = True):
        self.root_path = Path(root_path).resolve()
        self.repo_name = self.root_path.name
        self.output_file = output_file or f"{self.repo_name}_consolidated.txt"
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.max_file_size = max_file_size
        self.use_gitignore = use_gitignore
        
        # Initialize gitignore parser
        self.gitignore = GitignoreParser(self.root_path) if use_gitignore else None
        
        # Statistics
        self.files_processed = 0
        self.files_skipped = 0
        self.files_ignored = 0
        self.total_lines = 0
        self.total_size = 0
    
    def should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included"""
        # Always exclude certain files
        if file_path.name in ALWAYS_EXCLUDE_FILES:
            return False
        
        # Exclude output file if it exists in the current directory
        if file_path.resolve() == Path(self.output_file).resolve():
            return False
        
        # Check gitignore patterns
        if self.use_gitignore and self.gitignore:
            if self.gitignore.is_ignored(file_path, is_dir=False):
                self.files_ignored += 1
                return False
        
        # Check file size
        try:
            if file_path.stat().st_size > self.max_file_size:
                return False
        except:
            return False
        
        # Check if it's a special file
        if file_path.name in SPECIAL_FILES:
            return True
        
        # Check extensions
        return file_path.suffix.lower() in self.extensions
    
    def should_exclude_dir(self, dir_path: Path) -> bool:
        """Check if directory should be excluded"""
        # Always exclude certain directories
        if dir_path.name in ALWAYS_EXCLUDE_DIRS:
            return True
        
        # Check gitignore patterns
        if self.use_gitignore and self.gitignore:
            if self.gitignore.is_ignored(dir_path, is_dir=True):
                return True
        
        return False
    
    def collect_files(self) -> List[Dict]:
        """Collect all files to process"""
        files = []
        
        print("🔍 Discovering files...")
        for root, dirs, filenames in os.walk(self.root_path):
            root_path = Path(root)
            
            # Filter out excluded directories
            original_dirs = dirs[:]
            dirs[:] = []
            for d in original_dirs:
                dir_path = root_path / d
                if not self.should_exclude_dir(dir_path):
                    dirs.append(d)
                else:
                    if self.use_gitignore:
                        print(f"   Skipping directory: {dir_path.relative_to(self.root_path)}")
            
            for filename in filenames:
                file_path = root_path / filename
                if self.should_include_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.count('\n') + 1
                            
                        files.append({
                            'path': file_path.relative_to(self.root_path),
                            'content': content,
                            'lines': lines,
                            'size': file_path.stat().st_size
                        })
                        
                        self.files_processed += 1
                        self.total_lines += lines
                        self.total_size += file_path.stat().st_size
                        
                    except Exception as e:
                        print(f"⚠️  Error reading {file_path}: {e}")
                        self.files_skipped += 1
        
        # Sort files by path
        files.sort(key=lambda x: str(x['path']))
        return files
    
    def consolidate(self):
        """Main consolidation method"""
        print(f"\n🚀 PrepMate Quick Consolidator")
        print(f"{'='*50}")
        print(f"📁 Repository: {self.root_path}")
        print(f"📝 Output: {self.output_file}")
        print(f"🚫 Using .gitignore: {self.use_gitignore}")
        print(f"{'='*50}\n")
        
        # Collect files
        files = self.collect_files()
        
        if not files:
            print("❌ No files found!")
            return
        
        print(f"\n📊 Found {len(files)} files to consolidate")
        if self.files_ignored > 0:
            print(f"   Ignored {self.files_ignored} files from .gitignore patterns")
        print(f"📝 Writing consolidated output...")
        
        # Write output
        try:
            with open(self.output_file, 'w', encoding='utf-8') as out:
                # Header
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                out.write(f"{'='*60}\n")
                out.write(f"REPOSITORY: {self.repo_name}\n")
                out.write(f"GENERATED: {timestamp}\n")
                out.write(f"FILES: {self.files_processed}")
                if self.files_ignored > 0:
                    out.write(f" (ignored: {self.files_ignored})")
                if self.files_skipped > 0:
                    out.write(f" (errors: {self.files_skipped})")
                out.write("\n")
                out.write(f"TOTAL LINES: {self.total_lines:,}\n")
                out.write(f"TOTAL SIZE: {self.total_size / (1024*1024):.2f} MB\n")
                out.write(f"GITIGNORE: {'Yes' if self.use_gitignore else 'No'}\n")
                out.write(f"{'='*60}\n\n")
                
                # Table of contents
                out.write("TABLE OF CONTENTS:\n")
                out.write("="*60 + "\n")
                for i, file_info in enumerate(files, 1):
                    out.write(f"{i:4d}. {file_info['path']} ({file_info['lines']} lines)\n")
                out.write("="*60 + "\n")
                
                # File contents
                for i, file_info in enumerate(files, 1):
                    out.write(f"\n\n{'='*60}\n")
                    out.write(f"FILE {i}/{len(files)}: {file_info['path']}\n")
                    out.write(f"LINES: {file_info['lines']}\n")
                    out.write(f"{'='*60}\n\n")
                    out.write(file_info['content'])
                    if not file_info['content'].endswith('\n'):
                        out.write('\n')
        
        except Exception as e:
            print(f"❌ Error writing output: {e}")
            return
        
        # Summary
        print(f"\n✅ SUCCESS!")
        print(f"📊 Files processed: {self.files_processed}")
        if self.files_ignored > 0:
            print(f"🚫 Files ignored: {self.files_ignored}")
        print(f"📏 Total lines: {self.total_lines:,}")
        print(f"💾 Output size: {os.path.getsize(self.output_file) / (1024*1024):.2f} MB")
        print(f"📄 Output file: {self.output_file}")
        print(f"\n🎉 Repository consolidated!\n")


def main():
    """Command-line interface with argument parsing"""
    parser = argparse.ArgumentParser(
        description='PrepMate - Quick Repository Consolidator (with .gitignore support)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python prepmate.py                    # Consolidate current directory
    python prepmate.py ../myproject       # Consolidate specific directory
    python prepmate.py -o analysis.txt    # Custom output file
    python prepmate.py --no-gitignore     # Ignore .gitignore patterns
    python prepmate.py --max-size 5000000 # Set max file size to 5MB

Note: 
    - Respects .gitignore patterns by default
    - prepmate.py itself is always excluded
    - Output file is automatically excluded if in the repo
        """
    )
    
    parser.add_argument('path', nargs='?', default='.',
                        help='Path to repository (default: current directory)')
    parser.add_argument('-o', '--output', type=str,
                        help='Output file name')
    parser.add_argument('--no-gitignore', action='store_true',
                        help='Ignore .gitignore patterns')
    parser.add_argument('--max-size', type=int, default=1_000_000,
                        help='Maximum file size in bytes (default: 1MB)')
    parser.add_argument('--extensions', type=str,
                        help='Comma-separated list of extensions to include (e.g., ".py,.js,.md")')
    
    args = parser.parse_args()
    
    # Parse extensions if provided
    extensions = None
    if args.extensions:
        extensions = set(ext.strip() for ext in args.extensions.split(','))
        # Ensure extensions start with a dot
        extensions = {ext if ext.startswith('.') else f'.{ext}' for ext in extensions}
    
    # Run consolidation
    prep = QuickPrepMate(
        root_path=args.path,
        output_file=args.output,
        extensions=extensions,
        max_file_size=args.max_size,
        use_gitignore=not args.no_gitignore
    )
    prep.consolidate()


if __name__ == '__main__':
    main()