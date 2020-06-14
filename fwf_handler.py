import csv
import json
import time
from collections import OrderedDict

class FWFHandler(object):
    """Fixed-width file handler

    This class provides some basic tools for parsing fixed-width files
    based on the `tape` OrderedDict attribute. Currently this is a rough
    version and includes almost no error handling for the user, so one
    must be cautious to follow the desired tape conventions for success.

    Note: OrderedDict is unnecessary for Python 3.5+, but is still used
    for clarity of intention and backwards compatibility.

    Parameters
    ----------
    tape : OrderedDict, default = None
        Should be filled with an OrderedDict whose keys are feature names,
        and the value associated to each key is a tuple (start,end) of
        starting location (inclusive) and ending location (exclusive) for
        the character placement within the fixed-width file for that feature.

    """
    def __init__(self, tape = None):
        if isinstance(tape,dict):
            self.tape = OrderedDict(tape)
        else:
            self.tape = OrderedDict()

    @classmethod
    def from_json(cls, json_path):
        """Create a new FWFHandler object with tape loaded from json"""
        with open(json_path, 'r') as fin:
            return cls({key:tuple(val) for key,val in json.load(fin).items()})

    def add_key(self, key = None, start = None, end = None):
        """Add a new feature key to location tuple into the tape

        Args:
            key (string): Feature key to add to the tape.
            start (int): Starting character location (incl) within the fixed-width file.
            end (int): Ending character location (excl) within the fixed-width file.
        """
        if (key is None):
            key = str(input("Desired key name (do not use quotations): "))
        if (start is None):
            start = int(input("Starting location (inclusive): "))
        if (end is None):
            end = int(input("Ending location (exclusive): "))
        self.tape[key] = (start,end)
        print("*%s* is assigned location: %s" % (key, self.tape[key]))

    def alter_key_location(self, key, start = None, end = None):
        """Alter an existing feature key location tuple in the tape

        Args:
            key (string): Feature key to add to the tape.
            start (int): New starting character location (incl) within the fixed-width file.
            end (int): New ending character location (excl) within the fixed-width file.
        """
        if key not in self.tape:
            print("*%s* is not currently a key. Try `add_key` to insert a new key" % key)
        else:
            start_old, end_old = self.tape[key]
            if (start is None):
                print("Old starting location %s." % start_old, end = ' ')
                start = int(input("Enter new starting location (inclusive): "))
            if (end is None):
                print("Old ending location %s." % end_old, end = ' ')
                end = int(input("Enter new ending location (exclusive): "))
            self.add_key(key, start, end)

    def remove_key(self, key):
        """Remove a feature key and its location tuple from the tape"""
        if key in self.tape:
            vals = self.tape.pop(key)
            print("Removed *%s*, with assigned location: %s" % (key, vals))

    def inspect_tape(self):
        """Print out the current tape for inspection"""
        for idx, key in enumerate(self.tape):
            print("%s. *%s* is assigned location: %s" % (idx, key, self.tape[key]))

    def save_tape_as_json(self, output_path):
        """Save the current tape as a json file"""
        with open(tape_path, 'w') as fout:
            json.dump(self.tape, fout)
        return tape_path

    def to_csv(self, fwf_path, csv_path, verbose = False):
        """Convert the fixed-width format to csv with respect to the tape.

        This method uses the user-defined tape to parse a fixed-width
        file line-by-line, saving the parsed content as a csv file.
        The first row of the csv file will be the feature names defined
        by the feature keys within the tape.

        Args:
            fwf_path (string): Path to the fixed-width file.
            csv_path (string): Output path for the csv file.
            verbose (bool): Print out progress every 50000 lines. Default = False.

        Returns:
            Path to the created csv file.

        """
        with open(csv_path, 'w', newline='') as fout:
            writer = csv.writer(fout)
            col_names = self.tape.keys()
            writer.writerow(col_names)
            with open(fwf_path,'r') as fin:
                # character location tuples
                vals = self.tape.values()
                # start the timer
                stime = time.time()
                # begin line-by-line intake, parse, and transfer
                line = fin.readline()
                line_n = 1
                while line:
                    # print out every 100000 lines if verbose
                    if verbose:
                        if line_n%100000 == 0:
                            print("Line %s finished..." % line_n)
                    # parse the line and transfer to csv
                    writer.writerow(line[slice(*v)] for v in vals)
                    # iterate
                    line = fin.readline()
                    line_n += 1
                # end the timer
                etime = time.time()
                print("Finished at line %s in %.2f seconds." % (line_n-1, etime-stime))
        return csv_path
