"""
Update the mesh of the UPF file from PseudoDojo

NOTE: Should work with PseudoDojo files with a constant mesh spacing of 0.01 a_0

abinit has a cut off radius of 6 bohr, and any data points beyond are discarded,
in order to avoid numerical noisy.
CASTEP does not have such implementation, hence resulting in the differences when the same 
pseudopotential is used as input.
This script alters the UPF file to implement such cut off radius.
"""
from pathlib import Path
from datetime import datetime
import re

HEADERS = [
    'PP_CHI',
    'PP_R',
    'PP_RAB',
    'PP_LOCAL',
    'PP_BETA',
    'PP_NLCC',
    'PP_RHOATOM',
]

__version__ = "0.1.0"

class UpfTrimmer:
    """
    Class for trimming down a Upf file with a specific mesh size in order to
    manually implement a truncation of the data beyond a certain radius.
    """

    def __init__(self, lines:list, mesh:int, verbose=False):
        """Instantiate the timmer"""
        self.lines = lines
        self.mesh = mesh
        self.line_number = 0
        self.current_tag = None
        self.output_lines = []
        self.total_nlines = len(self.lines)
        self.current_size = None
        self.current_columns = None
        self.verbose = verbose

    def next_line(self):
        if self.line_number == self.total_nlines-1:
            return False
        self.line_number += 1
        return True

    @property
    def current_line(self):
        return self.lines[self.line_number]

    def goto_next_tag(self):
        """Jump to the next tag, no recording is made"""
        recording = False
        while True:
            line = self.current_line
            if re.match(r"<\w+", line):
                break
            if re.match(r"<", line):
                recording = True
            if recording:
                self.output_lines.append(line)

            # Break when reached the end of the file
            if not self.next_line():
                break

    def process_tag(self):
        """
        Process the data under a tag and jump to the next valid tag for processing.

        Note that not all tags contain data, some tags are just for fencing the section.
        """
        if self.current_line == '':
            return False

        self.current_size = None
        self.current_columns = None

        # Are we trimming this tag?
        tag_name = re.match(r'^<(\w+)', self.current_line).group(1)
        if not tag_name:
            raise RuntimeError("`process_tag` must be called when the current line is at a tag")
        self.log(f"Processing: {self.current_line}")
        trim = tag_name in HEADERS

        def replace_size(line):
            """Process and replace the 'size' field"""
            if "mesh_size" in self.current_line:
                new_line = re.sub(r'mesh_size="[0-9 ]+"',  f'mesh_size="   {self.mesh}"', line)
                self.output_lines.append(new_line)
            elif "size" in self.current_line and trim:
                self.current_size = int(re.search(r'size="([0-9 ]+)"', line).group(1).strip())
                new_line = re.sub(r'size="[0-9 ]+"',  f'size="{self.mesh}"', line)
                self.output_lines.append(new_line)
            else:
                self.output_lines.append(line)
            # Look for columns
            if 'columns' in self.current_line and trim: 
                self.current_columns = int(re.search(r'columns="([0-9 ]+)"', line).group(1).strip())

        # This is one-line tag
        if '>' in self.current_line:
            replace_size(self.current_line)
            self.next_line()
            # Return if we have already arrived at the next tag

            # Add some metadata lines to PP_INFO
            if tag_name == 'PP_INFO':
                content = f"""NOTE!!!!
This file is trimmed with a mesh size of {self.mesh} from the original version.
Trimming performed at {datetime.now()} by trim_upf.py version {__version__}
"""
                self.output_lines.append(content)


            if re.match("<\w+", self.current_line):
                return
        
        else:# Multiline tag
            while True:
                replace_size(self.current_line)
                if '>' in self.current_line:
                    self.next_line()
                    break
                self.next_line()

        # No trimming needed go to the next tag and record everything in between
        if not trim:
            self.log('not triming')
            while True:
                self.output_lines.append(self.current_line)
                self.next_line()
                if re.search(r"<\w", self.current_line):
                    # Arrived at the next tag so we return
                    return

        # Trim the content
        if self.current_size:
            self.log('triming')
            nlines = self.mesh // self.current_columns
            self.trim_content(nlines)
        return True

    def log(self, msg):
        """Logging messages"""
        if self.verbose:
            print(msg) 

    def trim_content(self, nlines):
        """
        Trim the content under the tag, then seek to the next tag
        """

        for i in range(nlines):
            self.output_lines.append(self.current_line)
            self.next_line()
        # Jump to the next tag
        self.goto_next_tag()

    @property
    def is_end_of_file(self):
        return self.line_number == self.total_nlines - 1

    def process_file(self, save=None):
        """
        Run the processing steps.

        The processed lines are saved in self.output_lines.
        """

        while True:
            flag = self.process_tag()
            if flag is False:
                break
        assert self.is_end_of_file

        self.log('Completed processing')
        self.log(f'Initial lines: {self.total_nlines}')
        self.log(f'Final   lines: {len(self.output_lines)}')
        if save is not None:
            self.save_output(save)

    def save_output(self, outfile:str):
        """Save the processed lines to a output file"""

        with open(outfile, "w", encoding='utf-8') as fhandle:
            for line in self.output_lines:
                if line:
                    fhandle.write(line + '\n') 



if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(prog='upftrim', description='Tool for trimming UPF files down to a certain mesh size')
    parser.add_argument('indir')
    parser.add_argument('outdir')
    parser.add_argument('--mesh', default=600, type=int)
    parser.add_argument('--verbose', default=False, action='store_true')

    args = parser.parse_args()
    upfs = Path(args.indir).glob("*.upf")
    Path(args.outdir).mkdir(exist_ok=True)

    for file in upfs:
        print(f"Processing upf: {file}")
        lines = file.read_text().split('\n')
        processor = UpfTrimmer(lines, args.mesh)
        processor.process_file(save=(Path(args.outdir) / file.name))
