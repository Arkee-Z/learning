#!/usr/bin/env python3
import argparse
import ctypes
import sys
import os
from pathlib import Path
from enum import IntEnum

def load_lib():
    if sys.platform == "win32":
        lib_name = "libtemp.dll"
    elif sys.platform == "darwin": # macOS
        lib_name = "libtemp.dylib"
    else:   # linux or other unix-like
        lib_name = "libtemp.so"

    lib_path = Path(__file__).parent / lib_name
    # print(lib_path)
    if not lib_path.exists():
        print(f"ERROR: cannot found {lib_path}. ", file=sys.stderr)
        sys.exit(1)

    # load dynamic library
    lib = ctypes.CDLL(str(lib_path))

    # declare function prototype
    FUNCS = {
        'F2C_converter': ([ctypes.c_float], ctypes.c_float),
        'C2F_converter': ([ctypes.c_float], ctypes.c_float),
        'print_temp_mapping_table': (
            [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_bool], 
            None    # void return
        ),
    }

    # login function
    for name, (argtypes, restype) in FUNCS.items():
        try:
            func = getattr(lib, name)
            func.argtypes = argtypes
            func.restype = restype
        except AttributeError:
            print(f"Warning: cannot found C function {name} ", file=sys.stderr)

    return lib

lib = load_lib()

class Converter(IntEnum):
    F2C = 0
    C2F = 1

def main():
    parser = argparse.ArgumentParser(
        prog="temp",
        description="Temperature Converter Tool ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
%(prog)s convert -f 100          # 华氏100度转摄氏
%(prog)s convert -c 37           # 摄氏37度转华氏
%(prog)s table -l 0 -u 100 -s 20 --f2c    # 打印华氏->摄氏映射表
%(prog)s table -l 0 -u 100 -s 10 --c2f -r # 反向打印摄氏->华氏表
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")

    # --- sub-command convert ---
    parser_convert = subparsers.add_parser("convert", help="单次温度转换")
    conv_group = parser_convert.add_mutually_exclusive_group(required=True)
    conv_group.add_argument("-f", "--fahr", type=float, help="convert to fahr")
    conv_group.add_argument("-c", "--cels", type=float, help="convert to celsius")

    # --- sub-command table ---
    parser_table = subparsers.add_parser("table", help="打印温度映射表格")
    parser_table.add_argument("-l", "--lower", type=int, required=False, default=0, help="起始温度")
    parser_table.add_argument("-u", "--upper", type=int, required=False, default=100, help="结束温度")
    parser_table.add_argument("-s", "--step", type=int, required=False, default=1, help="步长")

    table_group = parser_table.add_mutually_exclusive_group(required=True)
    table_group.add_argument("--f2c", action="store_true", help="fahr to celsius")
    table_group.add_argument("--c2f", action="store_true", help="celsius to fahr")

    parser_table.add_argument("-r", "--reverse", action="store_true", help="reverse print(high to low)")

    args = parser.parse_args()

    if args.command == "convert":
        if args.fahr is not None:
            result = lib.F2C_converter(args.fahr)
            print(f"{args.fahr:.2f}°F = {result:.2f}°C")
        else:
            result = lib.C2F_converter(args.cels)
            print(f"{args.cels:.2f}°C = {result:.2f}°F")
    elif args.command == "table":
        conv = Converter.F2C if args.f2c else Converter.C2F
        lib.print_temp_mapping_table(
            args.lower,
            args.upper,
            args.step,
            conv,
            args.reverse
        )
    
if __name__ == "__main__":
    main()