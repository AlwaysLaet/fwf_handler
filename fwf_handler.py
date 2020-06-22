import csv
import json
import time
import re
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
            return cls(json.load(fin))

    def add_key(self, key = None, start = None, end = None, dtype = None):
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
        self.tape[key] = dict(location = [start,end], dtype = dtype)
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
            print("%s. *%s*(%s) is assigned location: %s"
                  % (idx, key, self.table[key]['dtype'],self.tape[key]['location']))

    def save_tape_as_json(self, output_path):
        """Save the current tape as a json file"""
        with open(output_path, 'w') as fout:
            json.dump(self.tape, fout)
        return output_path

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
        # column names and character locations
        col_names = self.tape.keys()
        locs = [d['location'] for d in self.tape.values()]
        with open(csv_path, 'w', newline='') as fout:
            writer = csv.writer(fout)
            writer.writerow(col_names)
            with open(fwf_path,'r') as fin:
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
                    writer.writerow(line[slice(*s)] for s in locs)
                    # iterate
                    line = fin.readline()
                    line_n += 1
                # end the timer
                etime = time.time()
                print("Finished at line %s in %.2f seconds." % (line_n-1, etime-stime))
        return csv_path

    @staticmethod
    def infer_sql_dtypes(key_loc_dict, fwf_path, nlines_infer = 1000):
        """Infer the data types for importing into MySQL Table

        Args:
            key_loc_dict (dict): Key name paired with location tuple to infer data types
            fwf_path (str): File path to the fwf file to sample for inferring data type
            nlines_infer (int): Number of lines in fwf_path used to try to infer data type

        Returns:
            A dictionary of key to inferred SQL data type for the passed
            key_loc_dict.
        """
        lines = []
        # Keep keys and values corresponding
        use_dict = OrderedDict(key_loc_dict)
        col_names = use_dict.keys()
        locs = use_dict.values()
        if not locs:
            return {}
        with open(fwf_path, 'r') as fin:
            # Read through the first many lines of the fwf to infer data type
            line = fin.readline()
            lidx = 1
            while line and (lidx <= nlines_infer):
                lines.append( [line[slice(*s)] for s in locs] )
                line = fin.readline()
                lidx += 1
        cols = list(zip(col_names, zip(*lines)))
        dtypes = {}
        for key, col in cols:
            # Try type coercion to test for data type (rough and brute)
            col = [c for c in col if str(c).strip() != '']
            loc0, loc1 = self.tape[key]['location']
            if not col:
                dtypes[key] = "CHAR(%d)" % (loc1-loc0)
                continue
            try:
                # Is it an int?
                [int(c) for c in col]
                dtypes[key] = "INT"
                continue
            except:
                pass
            try:
                # Is it a float?
                [float(c) for c in col]
                dtypes[key] = "FLOAT"
                continue
            except:
                pass
            # Otherwise, default to character type
            dtypes[key] = "CHAR(%d)" % (loc1 - loc0)
        return dtypes

    def to_mysql_table_script(self,
                              table_name,
                              fwf_path,
                              sql_script_path = None,
                              infer_dtypes = True,
                              nlines_infer = 1000):
        """Create scripts to migrate the fixed-width file to a MySQL table

        Args:
            table_name (string): Desired name for SQL table
            fwf_path (string): Path to the fixed-width file
            sql_script_path (string or None): Path to save SQL script if desired, else None
            infer_dtypes (bool): If True, will infer SQL data type for unknown values
            nlines_infer (int): Max number of lines to use when inferring data type

        Returns:
            Tuple of strings, the first is a SQL command for creating a table based on the tape,
            the second for loading the fwf data into the table.
        """
        unknown_dtypes = [k:v['location'] for k,v in self.tape.items() if v['sql_dtype'] is None]
        if unknown_dtypes:
            if infer_dtypes:
                dtypes = self.infer_sql_dtypes(unknown_dtypes, fwf_path)
                for k,dtype in known.items():
                    self.tape[k]['sql_dtype'] = dtype
            else:
                for k in unknown_dtypes:
                    loc0,loc1 = self.tape[k]['location']
                    self.tape[k]['sql_dtype'] = "CHAR(%d)" % (loc1 - loc0)
        # String to create the table
        create_table_str = ("CREATE TABLE %s (\n\t" % table_name
                            + ",\n\t".join("%s %s" % (k,v['sql_dtype'])
                                           for k,v in self.tape.items())
                            + ");" )
        # String to load the data into the created table
        load_infile_str = ("LOAD DATA INFILE '%s' INTO TABLE %s\n\t(@var1)\n\tSET\n\t" % (fwf_path,table_name)
                           + ",\n\t".join("%s = SUBSTR(@var1,%d,%d)"
                                          % (k,v['location'][0]+1,v['location'][1]-v['location'][0])
                                          for k,v in self.tape.items())
                           + ";")
        # Save to a SQL script file if desired
        if sql_script_path:
            with open(sql_script_path, 'w') as fout:
                fout.writeline([create_table_str, load_infile_str])
        return create_table_str, load_infile_str
