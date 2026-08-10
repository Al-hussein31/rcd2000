"""M1 importer tests — pure logic, no Qt required.

Covers: format detection, unit parsing, alias mapping, module detection,
template round-trips, RCD2000 output parsing, clamping, and job building.
"""
import csv
import io
import os
import tempfile
import unittest

from rcd2000.gui import importer as I


class FormatDetectionTest(unittest.TestCase):
    def _write(self, text, ext=".csv"):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "file" + ext)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_csv_extension(self):
        self.assertEqual(I.detect_format(self._write("A,B\n1,2\n", ".csv")), "csv")

    def test_csv_by_content(self):
        self.assertEqual(I.detect_format(self._write("A,B\n1,2\n", ".txt")), "csv")

    def test_keyvalue(self):
        p = self._write("B = 300.mm\nH = 500.mm\nLOAD = 800.000kN\n", ".txt")
        self.assertEqual(I.detect_format(p), "keyvalue")

    def test_rcd2000_markers(self):
        for marker in ("Beam Id: B1", "Panel No. P4", "Column Ref: C1",
                       "Stair Ref: ST1", "Base Ref: F1", "Footing No. F2"):
            p = self._write("RCD2000 Ver 1.5\n" + marker + "\nSpan = 2m\n", ".txt")
            self.assertEqual(I.detect_format(p), "rcd2000", marker)

    def test_rcd2000_continuous_beam_line(self):
        p = self._write("Continuous Beam\nSpan 1 = 3.5m\n", ".txt")
        self.assertEqual(I.detect_format(p), "rcd2000")

    def test_jobjson(self):
        p = self._write('{"slug": "s", "name": "n", "items": []}', ".json")
        self.assertEqual(I.detect_format(p), "jobjson")

    def test_garbage_returns_none(self):
        p = self._write("not a design file at all\njust prose\n", ".txt")
        self.assertIsNone(I.detect_format(p))

    def test_empty_returns_none(self):
        self.assertIsNone(I.detect_format(self._write("   \n", ".txt")))

    def test_cont_beam_template_not_misdetected(self):
        # header starts with 'Continuous Beam Ref' — must be csv, not rcd2000
        p = os.path.join(tempfile.mkdtemp(), "cb.csv")
        I.write_template("cont_beam", p)
        self.assertEqual(I.detect_format(p), "csv")


class UnitParsingTest(unittest.TestCase):
    def test_bare_number(self):
        self.assertEqual(I.parse_value("3.5", ""), (3.5, None))

    def test_mm_conversion(self):
        self.assertEqual(I.parse_value("2200.mm", "m"), (2.2, None))

    def test_knm2_expected_kn_m_rejected(self):
        # kN/m2 (pressure) is not convertible to kN/m (line load)
        v, w = I.parse_value("18.2kN/m2", "kN/m")
        self.assertIsNone(v)
        self.assertIsNotNone(w)

    def test_n_mm2_to_kn_m2(self):
        self.assertEqual(I.parse_value("0.0182N/mm2", "kN/m2"), (18.2, None))

    def test_scientific_notation(self):
        self.assertEqual(I.parse_value("3.200E-04", "m4"), (3.2e-4, None))

    def test_commas(self):
        self.assertEqual(I.parse_value("1,200", "kN"), (1200.0, None))

    def test_unitless_accepts_any_unit(self):
        # no expected unit → recognised unit accepted verbatim
        self.assertEqual(I.parse_value("18.2kN/m", ""), (18.2, None))

    def test_garbage_returns_none(self):
        v, w = I.parse_value("abc", "m")
        self.assertIsNone(v)
        self.assertIsNotNone(w)

    def test_parse_int(self):
        self.assertEqual(I.parse_int("3"), (3, None))
        self.assertEqual(I.parse_int("3.5"), (4, None))  # rounds (count fields)
        v, w = I.parse_int("abc")
        self.assertIsNone(v)
        self.assertIsNotNone(w)


class MappingTest(unittest.TestCase):
    def test_column_alias_and_combo(self):
        s, l, w = I.map_row("column", {"load": "800", "bx": "300", "by": "300",
                                       "type": "Biaxial", "shape": "Rectangular"})
        self.assertEqual(s["load"], 800.0)
        self.assertEqual(s["col_type"], 2)
        self.assertEqual(s["shape"], 0)
        self.assertEqual(w, [])

    def test_beam_label(self):
        s, l, w = I.map_row("beam", {"beamid": "B1", "b": "300", "h": "500"})
        self.assertEqual(l, "B1")
        self.assertEqual(s["b_b"], 300.0)
        self.assertEqual(s["b_h"], 500.0)

    def test_member_arrays(self):
        s, l, w = I.map_row("beam", {"l1": "3.5", "l2": "4.0", "udl1": "18",
                                     "udl2": "16", "wt1": "3.5", "ab1": "2.5",
                                     "pl1": "40", "ap1": "1.5"})
        self.assertEqual(s["members"], [
            {"length": 3.5, "udl": 18.0, "wt": 3.5, "ab": 2.5, "pl": 40.0, "ap": 1.5},
            {"length": 4.0, "udl": 16.0},
        ])
        self.assertEqual(s["n_members"], 2)
        self.assertEqual(s["n_supports"], 3)

    def test_slab_cont_spans(self):
        s, l, w = I.map_row("slab", {"panelno": "S1", "type": "Continuous",
                                     "pl1": "40", "ap1": "1.5", "l2": "4.0",
                                     "udl2": "16"})
        self.assertEqual(s["slab_type"], 2)
        self.assertEqual(s["cont_spans"], [{"pl": 40.0, "ap": 1.5},
                                           {"length": 4.0, "udl": 16.0}])
        self.assertEqual(s["cont_nspan"], 2)

    def test_slab_panel_pls(self):
        s, l, w = I.map_row("slab", {"type": "Simply Supported",
                                     "pl1": "40", "ap1": "1.5"})
        self.assertEqual(s["slab_type"], 1)
        self.assertEqual(s["panel_pls"], [{"pl": 40.0, "ap": 1.5}])
        self.assertEqual(s["panel_npl"], 1)

    def test_cont_span_warning_when_not_continuous(self):
        # span columns with a non-continuous type → warning
        s, l, w = I.map_row("slab", {"type": "Simply Supported", "l2": "4.0"})
        self.assertTrue(any("Continuous" in x for x in w))
        self.assertEqual(s["slab_type"], 1)

    def test_section_size_beam(self):
        s, l, w = I.map_row("beam", {"sectionsize": "300 x 500"})
        self.assertEqual(s["b_b"], 300.0)
        self.assertEqual(s["b_h"], 500.0)

    def test_section_size_column(self):
        s, l, w = I.map_row("column", {"sectionsize": "300 x 450"})
        self.assertEqual(s["bx"], 300.0)
        self.assertEqual(s["by"], 450.0)

    def test_unknown_column_warning(self):
        s, l, w = I.map_row("beam", {"beamid": "B1", "frobnicate": "5"})
        self.assertEqual(l, "B1")
        self.assertTrue(any("frobnicate" in x for x in w))

    def test_negatives_clamped_with_warning(self):
        s, l, w = I.map_row("beam", {"l1": "-3.5", "udl1": "18"})
        self.assertEqual(s["members"][0]["length"], 0.0)
        self.assertTrue(any("outside supported range" in x for x in w))

    def test_column_bx_min_clamp(self):
        s, l, w = I.map_row("column", {"bx": "50", "by": "300"})
        self.assertEqual(s["bx"], 100.0)
        self.assertTrue(any("min 100" in x for x in w))

    def test_combo_parse_warning(self):
        s, l, w = I.map_row("column", {"type": "Nonsense"})
        self.assertNotIn("col_type", s)
        self.assertTrue(any("type" in x for x in w))

    def test_base_l1_is_plain_field(self):
        s, l, w = I.map_row("base", {"baseref": "F1", "l1": "2.0", "l2": "2.5"})
        self.assertEqual(s["base_l1"], 2.0)
        self.assertEqual(s["base_l2"], 2.5)
        self.assertEqual(w, [])

    def test_label_aliases_all_modules(self):
        for mod in ("column", "beam", "slab", "stair", "base", "cont_beam"):
            s, l, w = I.map_row(mod, {"label": "X1"})
            self.assertEqual(l, "X1", mod)


class TemplateRoundTripTest(unittest.TestCase):
    """Import a template file populated with one row → correct state."""

    def _roundtrip(self, module, sample):
        d = tempfile.mkdtemp()
        p = os.path.join(d, module + ".csv")
        I.write_template(module, p)
        lines = [l for l in open(p, encoding="utf-8").read().splitlines() if l]
        hdr = next(l for l in lines
                   if not l.lstrip().startswith("#")
                   and not l.lstrip().startswith('"#'))
        hdrs = next(csv.reader(io.StringIO(hdr)))
        row = ",".join(str(sample.get(I.norm_token(h), "")) for h in hdrs)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hdr + "\n" + row + "\n")
        t = I.parse_file(p)
        states, labels, warns = I.map_table(t.module_key, t.table)
        return t, states, labels, warns

    def test_beam_template(self):
        t, ss, ls, ws = self._roundtrip("beam", {
            "beamid": "B1", "fcu": 30, "fy": 500, "fyv": 250, "b": 300, "h": 500,
            "nsupports": 3, "nmembers": 2, "end1": "Pinned", "end2": "Fixed",
            "cantload2": 12, "cantmoment2": 3.5,
            "l1": 3.5, "l2": 3.5, "udl1": 18, "udl2": 16, "wt1": 3.5, "wb2": 4,
            "ab1": 2.5, "pl1": 40, "ap1": 1.5})
        self.assertEqual(t.module_key, "beam")
        s = ss[0]
        self.assertEqual(ls[0], "B1")
        self.assertEqual(s["n_members"], 2)
        self.assertEqual(s["n_supports"], 3)
        self.assertEqual(s["cant_load_2"], 12.0)
        self.assertEqual(s["members"][0]["length"], 3.5)
        self.assertEqual(s["members"][1]["wb"], 4.0)
        self.assertEqual(ws, [])

    def test_column_template(self):
        t, ss, ls, ws = self._roundtrip("column", {
            "columnid": "C1", "type": "Biaxial", "shape": "Rectangular",
            "load": 1200, "bx": 350, "by": 350, "dia": 20, "depth": 550,
            "length": 3.5, "le": 3.2, "lex": 3.2, "ley": 3.2, "fcu": 30,
            "fy": 500, "maxsteel": 4, "dh": 0.85, "mx": 120, "my": 80})
        s = ss[0]
        self.assertEqual(s["col_type"], 2)
        self.assertEqual(s["bx"], 350.0)
        self.assertEqual(s["col_max_steel"], 4.0)
        self.assertEqual(s["moment_x"], 120.0)

    def test_slab_template(self):
        t, ss, ls, ws = self._roundtrip("slab", {
            "panelno": "S1", "type": "Two-Way", "fcu": 30, "fy": 500,
            "depth": 150, "span": 4.5, "ly": 5.0, "case": 1, "spandepth": 30,
            "gk": 1.5, "qk": 3.0})
        s = ss[0]
        self.assertEqual(s["slab_type"], 3)
        self.assertEqual(s["s_depth"], 150.0)
        self.assertEqual(s["s_case"], 1)
        self.assertEqual(ws, [])

    def test_stair_template(self):
        t, ss, ls, ws = self._roundtrip("stair", {
            "stairref": "ST1", "span": 3.2, "tread": 250, "rise": 150,
            "imp": 3.0, "spl": 1.5, "wld": 25, "gk": 1.5, "qk": 3.0})
        s = ss[0]
        self.assertEqual(s["s_span"], 3.2)
        self.assertEqual(s["s_tread"], 250.0)
        self.assertEqual(s["s_wld"], 25.0)

    def test_base_template(self):
        t, ss, ls, ws = self._roundtrip("base", {
            "baseref": "F1", "type": "Square Isolated", "colshape": "Rectangular",
            "fcu": 30, "fy": 500, "pb": 150, "load": 800, "a1": 300, "a2": 300,
            "dia": 16, "h": 400, "l1": 2.0, "l2": 2.0, "dowel": 12,
            "gk": 1.5, "qk": 3.0})
        s = ss[0]
        self.assertEqual(s["base_type"], 0)
        self.assertEqual(s["base_l1"], 2.0)
        self.assertEqual(s["base_l2"], 2.0)
        self.assertEqual(s["base_load"], 800.0)
        self.assertEqual(ws, [])

    def test_cont_beam_template(self):
        t, ss, ls, ws = self._roundtrip("cont_beam", {
            "contbeamref": "CB1", "ns": 3, "nm": 2, "end1": "Pinned",
            "end2": "Fixed", "cantload2": 12, "cantmoment2": 3.5,
            "l1": 3.5, "l2": 4.0, "udl1": 18, "udl2": 16, "wt1": 3.5,
            "inertia1": 0.003, "e1": 1.0})
        s = ss[0]
        self.assertEqual(s["cb_ns"], 3)
        self.assertEqual(s["cb_end2"], 1)
        self.assertEqual(s["members"][0]["inertia"], 0.003)
        self.assertEqual(s["n_supports"], 3)


class RCD2000OutputTest(unittest.TestCase):
    def _parse(self, text):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "out.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return I.parse_file(p)

    def test_homogeneous_beam_file(self):
        t = self._parse("""RCD2000    Ver 1.5
JOB REF: Y2K13A
Beam Id: B1
Span Length = 2200.mm
UDL = 18.200kN/m
Cant Load 2 = -12.000kN/m
Section Size = 300 x 500

Beam Id: B2
Span Length = 3.500m
UDL = 16.000kN/m
Section Size = 250 x 450
""")
        self.assertEqual(t.module_key, "beam")
        self.assertEqual(t.job_ref, "Y2K13A")
        states, labels, warns = I.map_table(t.module_key, t.table)
        self.assertEqual(labels, ["B1", "B2"])
        self.assertEqual(states[0]["members"][0]["length"], 2.2)
        self.assertEqual(states[0]["cant_load_2"], 0.0)  # clamped
        self.assertTrue(any("outside supported range" in x for x in warns))
        self.assertEqual(states[1]["b_b"], 250.0)

    def test_continuous_beam_block(self):
        t = self._parse("""Continuous Beam
Span 1 = 3.500m
UDL 1 = 18.000kN/m
""")
        self.assertEqual(t.format, "rcd2000")
        self.assertEqual(t.module_key, "cont_beam")
        states, labels, warns = I.map_table("cont_beam", t.table)
        self.assertEqual(states[0]["members"], [{"length": 3.5, "udl": 18.0}])

    def test_mixed_file_needs_pick(self):
        t = self._parse("""Beam Id: B1
Span Length = 2m

Column Ref: C1
Load = 800kN
""")
        self.assertIsNone(t.module_key)
        states, labels, warns = I.map_table("beam", t.table)
        self.assertEqual(labels, ["B1", None])
        self.assertTrue(any("skipped" in x for x in warns))

    def test_unindexed_member_fields_go_to_member_1(self):
        t = self._parse("""Beam Id: B1
Span Length = 2m
UDL = 18kN/m
WT = 3.5kN/m
""")
        states, labels, warns = I.map_table("beam", t.table)
        self.assertEqual(states[0]["members"],
                         [{"length": 2.0, "udl": 18.0, "wt": 3.5}])


class JobBuildTest(unittest.TestCase):
    def test_build_job_items_and_labels(self):
        job = I.build_job("my job", None, [
            ("beam", {"b_b": 300.0, "b_h": 500.0}, "B1"),
            ("beam", {"b_b": 250.0, "b_h": 450.0}, "B2"),
        ])
        self.assertEqual(job.name, "my job")
        self.assertEqual([(i.label, i.type_key) for i in job.items],
                         [("B1", "beam"), ("B2", "beam")])
        self.assertEqual(job.items[0].state["b_b"], 300.0)

    def test_duplicate_labels_fall_back(self):
        # auto-generated labels (B2) when a label repeats
        job = I.build_job("j", None, [("beam", {}, "B1"), ("beam", {}, "B1")])
        self.assertEqual(job.items[0].label, "B1")
        self.assertEqual(job.items[1].label, "B2")

    def test_header_materials_consensus(self):
        hm = I.header_materials([
            {"col_fcu": 30.0, "col_fy": 500.0},
            {"col_fcu": 30.0, "col_fy": 500.0},
        ])
        self.assertEqual(hm, {"fcu": 30.0, "fy": 500.0})

    def test_header_materials_disagree_excluded(self):
        hm = I.header_materials([{"col_fcu": 30.0}, {"col_fcu": 35.0}])
        self.assertEqual(hm, {})

    def test_write_template_has_headers(self):
        d = tempfile.mkdtemp()
        for mod in ("column", "beam", "slab", "stair", "base", "cont_beam"):
            p = os.path.join(d, mod + ".csv")
            I.write_template(mod, p)
            content = open(p, encoding="utf-8").read()
            self.assertIn("[", content, mod)  # unit hints present


if __name__ == "__main__":
    unittest.main()
