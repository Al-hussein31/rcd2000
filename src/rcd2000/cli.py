#!/usr/bin/env python3
"""RCD2000 CLI - Reinforced Concrete Design to BS 8110.

Usage:
  rcd2000 beam <input.json> [options]
  rcd2000 column <input.json> [options]
  rcd2000 slab <input.json> [options]
  rcd2000 stair <input.json> [options]
  rcd2000 base <input.json> [options]
  rcd2000 continuous-beam <input.json> [options]
  rcd2000 info
"""
import sys
import json
import argparse
from typing import List

from rcd2000 import __version__
from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.stair import StairDesigner, StairInput
from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.continuous_beam import (
    ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember
)
from rcd2000.models import result_to_dict


def read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def write_output(data: dict, output: str):
    if output:
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Results written to {output}")
    else:
        print(json.dumps(data, indent=2, default=str))


def cmd_beam(args):
    data = read_json(args.input)
    fcu = data.get("fcu", 25.0)
    fy = data.get("fy", 460.0)
    fyv = data.get("fyv", 250.0)
    designer = BeamDesigner(fcu=fcu, fy=fy, fyv=fyv)

    beams = []
    for b in data.get("beams", [data]):
        member_pl = []
        for pl_list in b.get("member_pl", []):
            member_pl.append([(p["load"], p["dist"]) for p in pl_list])

        beams.append(BeamInput(
            beam_id=b.get("beam_id", "B1"),
            n_supports=b.get("n_supports", 2),
            n_members=b.get("n_members", 1),
            b=b.get("b", 225),
            bf=b.get("bf", 225),
            h=b.get("h", 450),
            hf=b.get("hf", 0),
            fcu=fcu, fy=fy, fyv=fyv,
            member_lengths=b.get("member_lengths", []),
            member_udl=b.get("member_udl", []),
            member_wt=b.get("member_wt", []),
            member_wb=b.get("member_wb", []),
            member_ab=b.get("member_ab", []),
            member_npl=b.get("member_npl", []),
            member_pl=member_pl,
            ty1=b.get("ty1", 0),
            ty2=b.get("ty2", 0),
        ))

    results = designer.design(beams)
    write_output({"results": [result_to_dict(r) for r in results]}, args.output)


def cmd_column(args):
    data = read_json(args.input)
    fcu = data.get("fcu", 25.0)
    fy = data.get("fy", 460.0)
    designer = ColumnDesigner(fcu=fcu, fy=fy)

    columns = []
    for c in data.get("columns", [data]):
        columns.append(ColumnInput(
            column_id=c.get("column_id", "C1"),
            col_type=c.get("col_type", 1),
            shape=c.get("shape", 1),
            load=c.get("load", 0),
            bx=c.get("bx", 0),
            by=c.get("by", 0),
            dia=c.get("dia", 0),
            depth=c.get("depth", 0),
            moment_x=c.get("moment_x", 0),
            moment_y=c.get("moment_y", 0),
            moment=c.get("moment", 0),
        ))

    results = designer.design(columns)
    write_output({"results": [result_to_dict(r) for r in results]}, args.output)


def cmd_slab(args):
    data = read_json(args.input)
    fcu = data.get("fcu", 25.0)
    fy = data.get("fy", 460.0)
    designer = SlabDesigner(fcu=fcu, fy=fy)

    panels = []
    for p in data.get("panels", [data]):
        panels.append(SlabPanelInput(
            panel_id=p.get("panel_id", "S1"),
            panel_type=p.get("panel_type", 1),
            depth=p.get("depth", 150),
            fcu=fcu, fy=fy,
            udl=p.get("udl", 0),
            span=p.get("span", 0),
            npl=p.get("npl", 0),
            point_loads=[(pl["load"], pl["dist"]) for pl in p.get("point_loads", [])],
            nspan=p.get("nspan", 0),
            span_lengths=p.get("span_lengths", []),
            span_udls=p.get("span_udls", []),
            ly=p.get("ly", 0),
            case=p.get("case", 0),
        ))

    results = designer.design(panels)
    write_output({"results": [result_to_dict(r) for r in results]}, args.output)


def cmd_stair(args):
    data = read_json(args.input)
    fcu = data.get("fcu", 25.0)
    fy = data.get("fy", 460.0)
    designer = StairDesigner(fcu=fcu, fy=fy)

    stairs = []
    for s in data.get("stairs", [data]):
        stairs.append(StairInput(
            stair_id=s.get("stair_id", "ST1"),
            span=s.get("span", 3.0),
            tread=s.get("tread", 250),
            rise=s.get("rise", 175),
            imposed_load=s.get("imposed_load", 1.5),
            spl=s.get("spl", 0),
            wld=s.get("wld", 0),
        ))

    results = designer.design(stairs)
    write_output({"results": [result_to_dict(r) for r in results]}, args.output)


def cmd_base(args):
    data = read_json(args.input)
    fcu = data.get("fcu", 25.0)
    fy = data.get("fy", 460.0)
    pb = data.get("pb", 150.0)
    designer = BaseDesigner(pb=pb, fcu=fcu, fy=fy)

    bases = []
    for b in data.get("bases", [data]):
        bases.append(BaseInput(
            base_id=b.get("base_id", "F1"),
            base_type=b.get("base_type", 1),
            col_type=b.get("col_type", 1),
            load=b.get("load", 0),
            pb=pb, fcu=fcu, fy=fy,
            a1=b.get("a1", 300),
            a2=b.get("a2", 300),
            dia=b.get("dia", 0),
            dowel_dia=b.get("dowel_dia", 12),
            h=b.get("h", 200),
            l1=b.get("l1", 0),
            l2=b.get("l2", 0),
        ))

    results = designer.design(bases)
    write_output({"results": [result_to_dict(r) for r in results]}, args.output)


def cmd_continuous(args):
    data = read_json(args.input)
    analyzer = ContinuousBeamAnalyzer()

    members = []
    for m in data.get("members", []):
        members.append(ContinuousBeamMember(
            member_id=m.get("member_id", "M1"),
            length=m.get("length", 0),
            inertia=m.get("inertia", 0.001),
            e_mod=m.get("e_mod", 1.0),
            udl=m.get("udl", 0),
            wt=m.get("wt", 0),
            wb=m.get("wb", 0),
            ab=m.get("ab", 0),
            npl=m.get("npl", 0),
            point_loads=[(pl["load"], pl["dist"]) for pl in m.get("point_loads", [])],
        ))

    beam = ContinuousBeamInput(
        n_supports=data.get("n_supports", 2),
        n_members=data.get("n_members", 1),
        members=members,
        end1_type=data.get("end1_type", 0),
        end2_type=data.get("end2_type", 0),
    )

    result = analyzer.analyze(beam)
    write_output(result_to_dict(result), args.output)


def cmd_info(args):
    print(f"RCD2000 v{__version__}")
    print("Reinforced Concrete Design to BS 8110:1997")
    print("Modules: beam, column, slab, stair, base, continuous-beam")
    print("Port of Oyenuga's RCD2000 FORTRAN programs")


def main():
    parser = argparse.ArgumentParser(
        description="RCD2000 - Reinforced Concrete Design to BS 8110",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    for cmd_name, help_text, func in [
        ("beam", "Design reinforced concrete beams", cmd_beam),
        ("column", "Design reinforced concrete columns", cmd_column),
        ("slab", "Design reinforced concrete slabs", cmd_slab),
        ("stair", "Design reinforced concrete stairs", cmd_stair),
        ("base", "Design reinforced concrete foundations", cmd_base),
        ("continuous-beam", "Analyze continuous beams (no design)", cmd_continuous),
        ("info", "Show version and module information", cmd_info),
    ]:
        p = sub.add_parser(cmd_name, help=help_text)
        if cmd_name != "info":
            p.add_argument("input", help="JSON input file")
            p.add_argument("-o", "--output", help="Output file (default: stdout)")
        p.set_defaults(func=func)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
