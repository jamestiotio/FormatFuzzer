import sys
import yaml

datatypes = {"u4": "uint32", "u1": "ubyte", "u2": "uint16"}  # TODO implement all types


class Converter(object):

    # TODO implement size lookup funtion

    def __init__(self, input_js, is_master=False, parent=None, root=None):
        print(self.__class__.__name__)
        self.output = []
        self.subtrees = {}
        self.this_level_keys = []
        self.input = input_js

        try:
            self.this_level_keys = self.input.keys()
        except:
            self.this_level_keys = None
        if is_master:
            self.root = self
            self.global_init()
            self.parse_subtree()
        else:
            self.parent = parent
            self.root = root

    def parse_subtree(self):
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                self.__dict__[local_key] = self.input[this_level_key]
                print(local_key)

                self.subtrees[local_key] = globals()[local_key](self.input[this_level_key], self, self.root)

                self.subtrees[local_key].parse_subtree()

    def generate_code_toplevel(self):
        self.output.extend(self.subtrees["enums"].generate_code())
        self.output.extend(self.subtrees["types"].generate_code())
        self.output.extend(self.subtrees["seq"].generate_code())

        return self.output

    def generate_code(self, size=None):
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                try:
                    self.output.extend(self.subtrees[local_key].generate_code(size))
                except Exception as err:
                    print("++++++START Converter codeGEN exception START +++++")
                    print(err)
                    print(self.subtrees[local_key].input)
                    print(self.this_level_keys)
                    print("++++++END Converter codeGEN exception END +++++")
                    pass
        return self.output

    def global_init(self):
        self.resolve_enum_sizes()

    def resolve_enum_sizes(self):
        self.enum_size = {"standard": "<byte>"}

    def lookup_enum_size(self, enum):
        return self.enum_size[enum]

    def lookup_enum_val_2_key(self, enum, key):

        inv_map = {v: k for k, v in self.enums[enum].items()}
        return inv_map[key]

    def expr_resolve(self, expr):
        if "::" in expr:
            return expr.split("::")
        elif False:
            pass
        # TODO MORE THINGS
        else:
            return expr

    def rec_search_flag_present(self, flag):
        try:
            if flag in self.this_level_keys:
                return True
            else:
                for this_level_key in self.this_level_keys:
                    local_key = remap_keys(this_level_key)
                    if local_key is not None:
                        if self.subtrees[local_key].rec_search_flag_present(flag):
                            return True
                        else:
                            pass
        except:
            return False

    def lookup_f_in_typ_pres(self, type, flag, id=None):
        if id is None:
            return self.subtrees["types"].subtrees[type].rec_search_flag_present(flag)
        return self.subtrees["types"].subtrees[type].subtrees[id].rec_search_flag_present(flag)


class meta(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        print(self.input)


class doc(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        self.output = "    //     " + str(self.input).replace("\n", "\n    //    ")

    def generate_code(self, size=None):
        return [self.output]


class doc_ref(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        self.output = "    //     " + str(self.input).replace("\n", "\n    //    ")

    def generate_code(self, size=None):
        return [self.output]


class enums(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                self.subtrees[local_key] = attribute(local_key, self.input[this_level_key])
                # print(str(self.subtrees[local_key].get_name()) + " : " + str(self.subtrees[local_key].get_value()))

    def generate_code(self, size=None):
        self.output = []
        for enum in self.subtrees.keys():
            self.output.extend(self.gen_single_enum(enum, self.subtrees[enum], converter.lookup_enum_size("standard")))
            self.output.append("\n")
        return self.output

    def gen_single_enum(self, key, enumerations, size="<byte>"):
        values = enumerations.get_value()
        lines = []
        # TODO FIND CORRECT TYPE? defaulting to <byte> for now
        lines.append("enum " + size + " {")
        keys = list(values.keys())
        for k in keys[0:-1]:
            lines.append("  " + (values[k] if "id" not in values[k] else values[k]["id"]) + " = " + str(k) + "," + (
                "" if "doc" not in values[k] else "     // " + (values[k]["doc"]).strip().replace("\n", "\n     //")))
        lines.append(
            "  " + (values[keys[-1]] if "id" not in values[keys[-1]] else values[keys[-1]]["id"]) + " = " + str(
                keys[-1]) + "" + (
                "" if "doc" not in values[keys[-1]] else "      // " + (values[keys[-1]]["doc"]).strip().replace("\n",
                                                                                                                 "\n     //")))
        lines.append("} " + str(key) + ";")
        return lines


class attribute():
    # A data_point is composed of mutiple attributes/they are the atomic informations
    # TODO CHECK IF CLASS IS ACTUALLY NEEDED
    def __init__(self, name, value):
        self.value = value
        self.name = name

    def get_value(self):
        return self.value

    def get_name(self):
        return self.name


class data_point():
    # Things that start with getting an id assigned/elements of seq
    def __init__(self, input_js, name=None, parent=None, root=None, size_eos=False):
        self.subtrees = dict()
        self.input = input_js
        self.id = name
        self.this_level_keys = self.input.keys()
        self.type = None
        self.size = None
        self.parent = parent
        self.root = root
        self.size_eos = size_eos

    def parse(self):
        if "type" in self.input.keys(): self.type = self.input["type"]
        if "size" in self.input.keys(): self.size = self.input["size"]
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                self.subtrees[local_key] = attribute(local_key, self.input[this_level_key])

            # print(str(self.subtrees[local_key].get_name()) + " : " + str(self.subtrees[local_key].get_value()))
        if self.id is None:
            self.id = self.subtrees["id"].get_value()

    def generate_code(self, size=None):
        # TODO EXTEND TO ALL VARIATIONS
        self.output = []
        self.front = []
        self.back = []

        if "process" in self.this_level_keys:
            self.gen_atomic(docu="IMPLEMENT" + str(self.input["process"]), size=size)
            print("PROCESS NOT IMPLEMENTED YET\n")
            # TODO IMPLEMENT
            self.output.extend(self.front)
            self.output.extend(self.back)
            return self.output
        elif "if" in self.this_level_keys:
            self.gen_if()
        elif "repeat" in self.this_level_keys:
            self.gen_repeat()

        if "encoding" in self.this_level_keys:
            self.gen_str()
        elif "contents" in self.this_level_keys:
            self.gen_contents()
        elif type(self.type) is dict:
            self.gen_switch(self.size)
        else:
            self.gen_atomic()

        self.output.extend(self.front)
        self.output.extend(self.back)
        return self.output

    def gen_switch(self, size=None):
        switch = self.type["switch-on"]
        cases = self.type["cases"]
        switch_drop = ["_root", "_parent", "_io"]
        if switch.split(".")[0] in switch_drop:
            switch_term = ".".join(switch.split(".")[1:])
        else:
            switch_term = switch
        self.front.append("     switch(" + str(switch_term) + ") {")
        for case_key in cases.keys():
            case = self.root.expr_resolve(case_key)
            if type(case) is list:
                case_val = self.root.lookup_enum_val_2_key(case[0], case[1])
            else:
                case_val = case
            if (self.root.lookup_f_in_typ_pres(cases[case_key], "size-eos") or (
                    self.root.lookup_f_in_typ_pres(cases[case_key], "repeat"))) and not self.root.lookup_f_in_typ_pres(
                cases[case_key], "encoding"):
                # TODO IMPLEMENT MISSING CASES AND FIX THE repeat CASE
                paramfield = "(" + str(size) + ")"
            else:
                paramfield = ""
            self.front.append("         case " + str(case_val) + ":")
            self.front.append("             " + str(cases[case_key]) + " " + str(self.id) + paramfield + ";")
            self.front.append("             break;")
        self.front.append("};")

    def gen_if(self):
        # TODO implement
        pass

    def gen_repeat(self):
        # TODO implement
        pass

    def gen_str(self):
        self.gen_atomic()
        # TODO THIS METHOD ONLY EXISTS IN CASE ENCODING NEEDS SPECIAL TREATMENT

    def gen_contents(self):
        # TODO implement
        pass

    def gen_atomic(self, docu="", size=None):
        if docu != "":
            loc_doc = "     //" + str(docu)
        else:
            loc_doc = ""

        if self.size_eos:
            print("size-EOS found here")
            pass
        if self.type == "str":
            if self.size is not None:
                # TODO IMPLEMENT CASE FOR DIFFERENT THAN ZEROBYTE TERMINATOR
                self.front.append("    char " + str(self.id) + "[" + str(self.size) + "]" + ";" + loc_doc)
            elif "size-eos" in self.input:
                self.front.append("    string " + str(self.id) + ";" + loc_doc)
        elif self.type == "strz":
            self.front.append("    string " + str(self.id) + ";" + loc_doc)
        elif self.type is not None:
            if self.type in datatypes.keys():  # BASIC TYPES
                self.front.append("    " + str(datatypes[self.type]) + " " + str(self.id) + ";" + loc_doc)
            else:  # CUSTOM TYPES
                self.front.append("    " + str(self.type) + " " + str(self.id) + ";" + loc_doc)
        elif self.size is not None:  # JUST BYTES
            self.front.append("    byte " + str(self.id) + "[" + str(self.size) + "]" + ";" + loc_doc)
        else:
            print(self.parent.input)
            # self.gen_repeat()

            print("ERROR NO SIZE OR TYPE GIVEN AND ITS NO MAGIC\n")
            self.front.append("//STUFF MISSING HERE @ NO MAGIC " + str(self.id) + " " + str(self.input))

    def rec_search_flag_present(self, flag):
        return flag in self.this_level_keys


class seq(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        self.this_level_keys = []
        for data_dict in self.input:
            # if this_level_key == "doc-ref":this_level_key="doc"
            self.subtrees[data_dict["id"]] = data_point(data_dict, parent=self, root=self.root)
            self.subtrees[data_dict["id"]].parse()
            self.this_level_keys.append(data_dict["id"])

    def generate_code(self, size=None):
        for this_level_key in self.this_level_keys:
            self.output.extend(self.subtrees[this_level_key].generate_code(size))
        # print("SEQ"+str(self.output)+str(self.input))
        return self.output


class instances(seq):

    def __init__(self, input_js, parent, root):
        seq.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                self.subtrees[local_key] = data_point(self.input[local_key], name=local_key, parent=self,
                                                      root=self.root)
                self.subtrees[local_key].parse()

    def generate_code(self, size=None):
        # TODO understand what these are exactly supposed to do as the are not parsed
        pass


class types(Converter):
    def __init__(self, input_js, parent, root):
        Converter.__init__(self, input_js, parent=parent, root=root)

    def parse_subtree(self):
        for this_level_key in self.this_level_keys:
            local_key = remap_keys(this_level_key)
            if local_key is not None:
                self.subtrees[local_key] = Converter(self.input[this_level_key], parent=self, root=self.root)
                self.subtrees[local_key].parse_subtree()

    def generate_code(self, size=None):
        self.output.extend(self.gen_forward_types())
        self.output.extend(self.gen_complete_types(size))
        return self.output

    def gen_complete_types(self, size=None):
        output = []
        if size is not None:
            lenfield = "(int32 lenght)"
        else:
            lenfield = ""
        for this_level_key in self.this_level_keys:
            if self.subtrees[this_level_key].rec_search_flag_present("size-eos") and not self.subtrees[
                this_level_key].rec_search_flag_present("encoding"):
                lenfield = "(int32 lenght)"
            output.append("struct " + str(this_level_key) + lenfield + " {")
            # TODO IMPLEMENT size Calc locals
            output.extend(self.subtrees[this_level_key].generate_code(size))
            output.append("};")
        return output
        # TODO IMPLEMENT THIS IS JUST A PLACEHOLDER

    def gen_forward_types(self):
        output = []
        for this_level_key in self.this_level_keys:
            output.append("struct " + str(this_level_key) + ";")
        return output


def remap_keys(key):
    remap = {"doc-ref": "doc_ref"}
    blocklist = ["-webide-representation"]
    if key in blocklist: return None
    if key in remap.keys(): return remap[key]
    return key


def main():
    global converter

    if len(sys.argv) != 3:
        print("USAGE = python3 Converter.py <input file path> <output file path>")  # TODO
        exit(1)
    input_file_name = sys.argv[1]
    output_file_name = sys.argv[2]
    with open(input_file_name, "r") as in_file:
        input_file = in_file.read()
    kaitaijs = yaml.load(input_file)

    converter = Converter(kaitaijs, True)

    # output = converter.generate_code()
    output = converter.generate_code_toplevel()
    # print('\n'.join(output))
    # converter.print_input()

    with open(output_file_name, "w") as out_file:
        out_file.write('\n'.join(output))

    print('\n'.join(output))


if __name__ == "__main__":
    main()