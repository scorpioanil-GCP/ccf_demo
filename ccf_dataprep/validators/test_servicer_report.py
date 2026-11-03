"""Tests for `ccf.servicer_report` — the two-format servicer report parser.

Fixtures below are REAL excerpts, byte-for-byte, cut out of the actual
2026-06 filings already on disk at:

    sources/absee/sdart-2022-6/servicer-2026-06.htm   (numbered / Santander)
    sources/absee/taot-2022-b/servicer-2026-06.htm    (labelled / Toyota)

They are not read from disk at test time -- see task brief constraint #2 --
so they are pasted in verbatim, tag soup and all. The Toyota fixture is
three separate real slices from three different pages of the same filing
(note balance/OC section, pool-data/net-loss section, delinquency section),
concatenated; each slice is untouched, only the gaps between them removed.

## The oracle values here are NOT the brief's table, and that is deliberate

The brief's Known-good-values table gives SDART 2022-6 oracles that were
cross-checked here against the actual on-disk 2026-06 file and DO NOT
MATCH IT -- pool_balance, oc_target, oc_amount, oc_percent, and
receivable_count all differ from what `servicer-2026-06.htm` actually
contains, and none of the brief's SDART figures (301051961.82, 99490728.43,
22738, ...) appear anywhere in any SDART servicer report across the full
12-month window, in either SDART deal. delinquency_percent=10.79 and
delinquency_trigger=24.00 DO match, but 10.79 turns out to be SDART
2022-6's *2026-05* value, not its 2026-06 one (24.00% is a static policy
threshold unchanged month to month, so it matches either period). The
Toyota oracle table, by contrast, matches the actual 2026-06 file exactly
on every field.

Since fixtures must be faithful excerpts of the real filed document (task
brief constraint #2) and a test oracle that contradicts the document it is
supposedly checking is worse than no oracle, the SDART oracle values used
below are the actual verified 2026-06 figures, cross-checked two ways: (a)
they are literally what appears in the fixture text, and (b) they are
internally consistent (sixty_day_delinquent_balance / pool_balance ==
delinquency_percent; oc_target - pool_balance's implied floor lines up with
oc_amount at this seasoning). This discrepancy is reported upstream
separately; it is not silently "fixed" by loosening a pattern to match a
number that does not appear in the source document, which is exactly the
failure mode the brief warns against.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from ccf.servicer_report import (
    UnparseableServicerReport,
    _item_value_zone,
    _leading_numeric_tokens,
    _numbered_single,
    _parse_numbered,
    _strip_html,
    detect_format,
    parse_servicer_report,
)

SDART_2026_06_EXCERPT = """{63} Targeted Overcollateralization</B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B>&nbsp;</B></P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{63}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">103,857,109.35</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B></B><B></B>{i}</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="top" COLSPAN="28"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>22.80%</B> of the Pool Balance of the last day of the related Collection Period and</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="top"><B>&nbsp;</B></TD>
<TD VALIGN="top" ALIGN="right"><B>{i}</B></TD>
<TD NOWRAP VALIGN="top"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="top">&nbsp;</TD>
<TD VALIGN="top" ALIGN="right">73,006,228.21</TD>
<TD NOWRAP VALIGN="top">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B></B><B></B>{ii}</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="top" COLSPAN="28"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>1.50%</B> of the Pool Balance as of the <FONT STYLE="white-space:nowrap">Cut-off</FONT>
Date</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{ii}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">30,850,881.14</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{64} </B>End of period Principal Balance of the Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{64}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">320,202,755.30</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{65} </B>End of period Note Balance</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{65}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">216,345,645.95</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{66} </B>Overcollateralization amount at the end of the Collection Period</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{66}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">103,857,109.35</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{67} </B>Overcollateralization % at the end of the Collection Period</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{67}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">32.43</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B><U>VI. STATISTICAL DATA</U></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B>&nbsp;</B></P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="13" COLSPAN="27"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD COLSPAN="26" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Original</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Previous</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Current</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{68} </B>Principal Balance of the Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{68}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2,056,725,409.43</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">340,076,028.22</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">320,202,755.30</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{69} </B>Weighted average coupon of the Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{69}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">15.18</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">14.42</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">14.41</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{70} </B>Weighted average original term of the Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{70}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">71.30</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">71.97</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">71.98</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{71} </B>Weighted average remaining term of the Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{71}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">68.94</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">28.18</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">27.28</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{72} </B>Number of Receivables</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{72}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">75,962</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">24,320</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">23,525</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B><U>VII. DELINQUENCY</U></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B>&nbsp;</B></P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="13" COLSPAN="27"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD COLSPAN="26" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Units</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Dollars</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Percentage</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B></B><B></B>Receivables with Scheduled Payment Delinquent</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{73} </B><FONT STYLE="white-space:nowrap">31-60</FONT> days</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{73}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2,989</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">48,156,004.10</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">15.04</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{74} </B><FONT STYLE="white-space:nowrap">61-90</FONT> days</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{74}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,555</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">26,275,594.47</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">8.21</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{75} </B><FONT STYLE="white-space:nowrap">91-120</FONT> days</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{75}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">433</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">7,168,719.56</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.24</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{76} </B>121 &#43; days delinquent</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{76}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom" ALIGN="right">&#8212;&#8194;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom" ALIGN="right">&#8212;&#8194;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.00</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{77} </B>Total</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{77}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">4,977</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">81,600,318.13</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">25.48</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{78} </B>Aggregate Principal Balance of 60 Day Delinquent Receivables (all Receivables that
are 60 or more days delinquent as of End of Collection Period)</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{78}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">35,784,723.53</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{79} </B>Delinquency Percentage as of the End of the Collection Period</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{79}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">11.18</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{80} </B>Delinquency Trigger</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{80}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">24.00</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{81} </B>Delinquency Trigger Occurred</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{81}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">No</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B><U>VIII. REPOSSESSION INVENTORY</U></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B>&nbsp;</B></P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="13" COLSPAN="27"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD COLSPAN="26" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Units</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Dollars</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{82} </B>Beginning of period Repossessed Inventory
<B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{82}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">282</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">5,492,899.17</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{83} </B>Vehicles Repossessed in current period <B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{83}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">263</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">4,894,550.52</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{84} </B>Repossessed vehicles sold in current period
<B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{84}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">199</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">3,954,178.67</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{85} </B>Repossessed vehicles reinstated in current period
<B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{85}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">35</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">564,697.07</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{86} </B>Repossessed vehicle adjustment in current period
<B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{86}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom" ALIGN="right">&#8212;&#8194;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">(160.94</TD>
<TD NOWRAP VALIGN="bottom">)&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{87} </B>End of period Repossessed Inventory <B></B><B></B><B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{87}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">311</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">5,868,413.01</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B><U>IX. CUMULATIVE NET LOSS RATIO</U></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B>&nbsp;</B></P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="13" COLSPAN="27"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD COLSPAN="26" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Units (a)</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Dollars</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{88} </B>Receivables becoming Defaulted Receivables during period
<B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{88}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">224</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">3,627,809.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{89} </B>Cram Down Losses occurring during period <B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{89}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">13</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">37,277.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{90} </B>Liquidation Proceeds collected during period <B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{90}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,167</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2,091,027.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{91} </B>Net losses during period <B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{91}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,574,059.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B></B><B></B>(a) Unit count represents # of instances in period per line item
<B></B><B></B><B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B><B></B><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="13" COLSPAN="27"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD>
<TD HEIGHT="13" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD COLSPAN="26" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD COLSPAN="2" VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Net Loss for<BR>Period</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Avg. Portfolio<BR>Balance (b)</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" ALIGN="center" STYLE="border-bottom:1.00pt solid #000000"><B>Net Loss<BR>Ratio (c)</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{92} </B>Current Period Net Loss Ratio</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{92}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,574,059.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">330,139,391.76</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.48</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{93} </B>Prior Period Net Loss Ratio</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{93}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,293,403.95</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">349,539,957.54</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.37</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{94} </B>Second Prior Period Net Loss Ratio</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{94}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,646,953.80</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">369,217,854.86</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.45</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{95} </B>Third Prior Period Net Loss Ratio</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{95}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,175,933.12</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">390,416,043.57</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.30</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{96} </B>Rolling 3 prior month average Net Loss Ratio</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{96}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.37</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="34"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial">(b) Average Portfolio Balance calculated using (Beginning of Period Aggregate Balance &#43; End
of Period Aggregate Balance)/2</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial">&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:3.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial">(c) Net Loss Ratio calculated using Net Loss for Period/Average Portfolio Balance for
Period</P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial">&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{97} </B>Cumulative Net losses since <FONT STYLE="white-space:nowrap">Cut-off</FONT> Date
(beginning of period) <B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{97}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">248,551,151.24</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{98} </B>Net losses during period <B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{98}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1,574,059.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{99} </B>Other Adjustments <B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{99}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD NOWRAP VALIGN="bottom" ALIGN="right">&#8212;&#8194;</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{100} </B>Cumulative Net losses since <FONT STYLE="white-space:nowrap">Cut-off</FONT> Date
(end of period) <B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{100}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">250,125,211.16</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="35"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="34"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:2.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B>{101} </B>Cumulative Net Loss Ratio (Net losses since the
<FONT STYLE="white-space:nowrap">Cut-off</FONT> Date / Pool Balance as of the <FONT STYLE="white-space:nowrap">Cut-off</FONT> Date) <B></B></P></TD>
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:0em; text-indent:0em; font-size:8pt; font-family:Arial"><B></B><B></B>&nbsp;</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom" ALIGN="right"><B>{101}</B></TD>
<TD NOWRAP VALIGN="bottom"><B>&nbsp;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">12.16</TD>
<TD NOWRAP VALIGN="bottom">%&nbsp;</TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8" COLSPAN="27"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR BGCOLOR="#cceeff" STYLE="page-break-inside:avoid ; font-family:Arial; font-size:8pt">
<TD VALIGN="top" COLSPAN="26"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:8pt; font-family:Arial"><B><U>"""

TAOT_2026_06_EXCERPT = (
    """<P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Adjusted Pool Balance</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$80,453,472.38</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Reserve Account Required Amount</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$0.00</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;&nbsp;&nbsp;&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Total Note Balance</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$0.00</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Reserve Account Release to Seller</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$4,250,000.02</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;&nbsp;&nbsp;&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Ending Overcollateralization Amount</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$80,453,472.38</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Ending Reserve Account Balance</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$0.00</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;&nbsp;&nbsp;&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Overcollateralization Target Amount</P></TD>
<TD VALIGN="bottom">&nbsp;&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$14,450,000.06</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
</TABLE>
 <p STYLE="margin-top:0pt;margin-bottom:0pt ; font-size:8pt">&nbsp;</P> <P STYLE="margin-top:0pt; margin-bottom:0pt; font-size:7pt; font-family:Times New Roman" ALIGN="center">Page 1 of 6 </P>

</DIV></Center>


<p style="margin-top:1em; margin-bottom:0em; page-break-before:always"> </p>
<HR SIZE="3" style="COLOR:#999999" WIDTH="100%" ALIGN="CENTER">


<Center><DIV STYLE="width:8.5in" align="left">

 <P STYLE="margin-top:0pt; margin-bottom:0pt; font-size:10pt; font-family:Times New Roman" ALIGN="center"><B>Servicer&#8217;s Certificate </B>"""
    """<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$8,854.18</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$8,945.35</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Cumulative Net Loss Ratio</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.38001%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.38233%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.38676%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.38609%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Repossessed in Current Period</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="center">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="5" ALIGN="center">5 vehicles</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
</TABLE> <P STYLE="font-size:12pt;margin-top:0pt;margin-bottom:0pt">&nbsp;</P><div style="max-width:100%;margin-left:0%; margin-right:0%;border:solid 1px;background-color:;;padding-top:2pt;padding-bottom:3pt">
<P STYLE="margin-top:0pt; margin-bottom:0pt; padding-top:0pt; font-size:7pt; font-family:Times New Roman"><B>&#8201;Pool Data </B></P></div> <P STYLE="font-size:12pt;margin-top:0pt;margin-bottom:0pt">&nbsp;</P>
<TABLE CELLSPACING="0" CELLPADDING="0" WIDTH="100%" BORDER="0" STYLE="BORDER-COLLAPSE:COLLAPSE; font-family:Times New Roman; font-size:7pt" ALIGN="center">


<TR>

<TD WIDTH="92%"></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8194;&#8195;&#8195;&#8195;&#8195;Original&#8195;&#8195;&#8195;&#8195;&#8194;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8195;&#8195;&#8195;Prior&nbsp;Month&#8195;&#8195;&#8195;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8195;&#8195;&#8195;Current&nbsp;Month&#8195;&#8195;&#8195;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center"><B>&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;&#8195;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>


<TR STYLE="font-size:1pt">
<TD HEIGHT="8"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Receivables Pool Balance</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$1,836,639,189.92</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$93,421,548.24</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$81,727,263.10</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Number of Contracts</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">77,626</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">18,326</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">16,779</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">"""
    """<div style="max-width:100%;margin-left:0%; margin-right:0%;border:solid 1px;background-color:;;padding-top:2pt;padding-bottom:3pt">
<P STYLE="margin-top:0pt; margin-bottom:0pt; padding-top:0pt; font-size:7pt; font-family:Times New Roman"><B>&#8201;Delinquent and Repossessed Contracts </B></P></div> <P STYLE="font-size:6pt;margin-top:0pt;margin-bottom:0pt">&nbsp;</P>
<TABLE CELLSPACING="0" CELLPADDING="0" WIDTH="100%" BORDER="0" STYLE="BORDER-COLLAPSE:COLLAPSE; font-family:Times New Roman; font-size:7pt" ALIGN="center">


<TR>

<TD WIDTH="92%"></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="4"></TD>
<TD HEIGHT="4" COLSPAN="4"></TD>
<TD HEIGHT="4" COLSPAN="4"></TD>
<TD HEIGHT="4" COLSPAN="4"></TD>
<TD HEIGHT="4" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8201;Percentage&nbsp;of&nbsp;Current&nbsp;Month&#8201;<BR>Number&nbsp;of&nbsp;Contracts</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8196;&#8195;&#8195;&#8195;&#8195;&#8195;Units&#8195;&#8195;&#8195;&#8195;&#8195;&#8196;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8201;Percentage&nbsp;of&nbsp;Current&nbsp;Month&#8201;<BR>Receivables&nbsp;Pool&nbsp;Balance</B></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="2" NOWRAP ALIGN="center" STYLE="border-bottom:1.00px solid #000000"><B>&#8195;&#8195;&#8195;&#8195;&#8195;Balance&#8195;&#8195;&#8195;&#8195;&#8195;</B></TD>
<TD VALIGN="bottom">&nbsp;</TD></TR>


<TR STYLE="font-size:1pt">
<TD HEIGHT="8"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman"><FONT STYLE="white-space:nowrap">30-59</FONT> Days Delinquent</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.03%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">341</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">3.53%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$2,888,411.41</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman"><FONT STYLE="white-space:nowrap">60-89</FONT> Days Delinquent</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.61%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">103</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1.04%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$848,076.70</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman"><FONT STYLE="white-space:nowrap">90-119</FONT> Days Delinquent</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.17%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">28</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.27%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$221,665.08</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">120 or more Days Delinquent</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.00%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">0.00%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$0.00</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1px; ">
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:1.00px solid #000000">&nbsp;</P></TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:1.00px solid #000000">&nbsp;</P></TD>
<TD>&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:1.00px solid #000000">&nbsp;</P></TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:1.00px solid #000000">&nbsp;</P></TD>
<TD>&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Total Delinquencies</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.81%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">472</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">4.84%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$3,958,153.19</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD></TR>
<TR STYLE="font-size:1px; ">
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:3.00px double #000000">&nbsp;</P></TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:3.00px double #000000">&nbsp;</P></TD>
<TD>&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:3.00px double #000000">&nbsp;</P></TD>
<TD VALIGN="bottom"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; border-top:3.00px double #000000">&nbsp;</P></TD>
<TD>&nbsp;</TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Total Delinquencies - Prior Period</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.64%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">4.43%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Total Delinquencies - Two Months Prior</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.26%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">3.85%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Total Delinquencies - Three Months Prior</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">2.13%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">3.52%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="font-size:1pt">
<TD HEIGHT="8"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD>
<TD HEIGHT="8" COLSPAN="4"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Receivables Pool Balance</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">$81,727,263.10</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman"><FONT STYLE="white-space:nowrap">60-Day</FONT> Delinquency Percentage</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">1.31%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Delinquency Trigger Percentage</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">4.65%</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR>
<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Has a Delinquency Trigger occurred in this Collection Period?</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="right">No</TD>
<TD NOWRAP VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD></TR></TABLE> <P STYLE="font-size:12pt;margin-top:0pt;margin-bottom:0pt">&nbsp;</P>
<TABLE CELLSPACING="0" CELLPADDING="0" WIDTH="100%" BORDER="0" STYLE="BORDER-COLLAPSE:COLLAPSE; font-family:Times New Roman; font-size:7pt" ALIGN="center">


<TR>

<TD WIDTH="92%"></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD>

<TD VALIGN="bottom" WIDTH="1%"></TD>
<TD></TD>
<TD></TD>
<TD></TD></TR>


<TR STYLE="page-break-inside:avoid ; font-family:Times New Roman; font-size:7pt">
<TD VALIGN="top"> <P STYLE=" margin-top:0pt ; margin-bottom:0pt; margin-left:1.00em; text-indent:-1.00em; font-size:7pt; font-family:Times New Roman">Repossessed Vehicle Inventory*</P></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom"></TD>
<TD VALIGN="bottom">&nbsp;</TD>
<TD VALIGN="bottom" ALIGN="center">&nbsp;</TD>
<TD VALIGN="bottom" COLSPAN="5" ALIGN="center">"""
)


# --------------------------------------------------------------------------
# Real oracle values, verified directly against the fixtures above.
# --------------------------------------------------------------------------

SDART_ORACLE = {
    "pool_balance": Decimal("320202755.30"),
    "note_balance": Decimal("216345645.95"),
    "oc_amount": Decimal("103857109.35"),
    "oc_percent": Decimal("32.43"),
    "oc_target": Decimal("103857109.35"),
    "delinquency_percent": Decimal("11.18"),
    "delinquency_trigger": Decimal("24.00"),
    "trigger_occurred": False,
    "sixty_day_delinquent_balance": Decimal("35784723.53"),
    "cumulative_net_loss_percent": Decimal("12.16"),
    "receivable_count": 23525,
}

TAOT_ORACLE = {
    "pool_balance": Decimal("81727263.10"),
    "note_balance": Decimal("0.00"),
    "oc_amount": Decimal("80453472.38"),
    "oc_percent": None,
    "oc_target": Decimal("14450000.06"),
    "delinquency_percent": Decimal("1.31"),
    "delinquency_trigger": Decimal("4.65"),
    "trigger_occurred": False,
    "sixty_day_delinquent_balance": None,
    "cumulative_net_loss_percent": Decimal("0.38001"),
    "receivable_count": 16779,
}


def test_detects_numbered_format():
    assert detect_format(SDART_2026_06_EXCERPT) == "numbered"


def test_detects_labelled_format():
    assert detect_format(TAOT_2026_06_EXCERPT) == "labelled"


def test_numbered_reads_every_oracle_field():
    out = parse_servicer_report(SDART_2026_06_EXCERPT)
    assert out["source_format"] == "numbered"
    for key, expected in SDART_ORACLE.items():
        assert out[key] == expected, f"{key}: got {out[key]!r}, expected {expected!r}"


def test_labelled_reads_every_oracle_field():
    out = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert out["source_format"] == "labelled"
    for key, expected in TAOT_ORACLE.items():
        assert out[key] == expected, f"{key}: got {out[key]!r}, expected {expected!r}"


def test_toyota_oc_percent_is_none_not_zero():
    """Toyota does not publish it. None means 'not published'; 0.00 would be
    a claim the filing does not make."""
    out = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert out["oc_percent"] is None
    assert out["oc_percent"] != Decimal("0")


def test_toyota_sixty_day_delinquent_balance_is_none_not_computed():
    """Toyota publishes per-bucket balances and a 60-day PERCENTAGE, but
    never a single filed 60+ day BALANCE. Summing the buckets ourselves
    would present our arithmetic as the servicer's."""
    out = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert out["sixty_day_delinquent_balance"] is None


def test_trigger_occurred_captured_as_evidence_only():
    """Captured because a disagreement with our own recomputation is a
    finding. Never read as the answer to 'did the trigger occur'."""
    numbered = parse_servicer_report(SDART_2026_06_EXCERPT)
    labelled = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert numbered["trigger_occurred"] is False
    assert labelled["trigger_occurred"] is False
    # It is a plain bool field alongside the rest of the evidence -- nothing
    # in this module treats it as authoritative or gates on it.
    assert isinstance(numbered["trigger_occurred"], bool)
    assert isinstance(labelled["trigger_occurred"], bool)


def test_bucket_boundaries_are_labelled_per_issuer():
    """Buckets come back keyed by the issuer's OWN boundaries, so a caller
    cannot accidentally add 61-90 to 60-89 and call it a total."""
    numbered = parse_servicer_report(SDART_2026_06_EXCERPT)
    labelled = parse_servicer_report(TAOT_2026_06_EXCERPT)

    assert set(numbered["delinquency_buckets"]) == {"31-60", "61-90", "91-120", "121+"}
    assert set(labelled["delinquency_buckets"]) == {"30-59", "60-89", "90-119", "120+"}

    sdart_60_90 = numbered["delinquency_buckets"]["61-90"]
    assert sdart_60_90["count"] == 1555
    assert sdart_60_90["balance"] == Decimal("26275594.47")
    assert sdart_60_90["percent"] == Decimal("8.21")

    taot_60_89 = labelled["delinquency_buckets"]["60-89"]
    assert taot_60_89["count"] == 103
    assert taot_60_89["balance"] == Decimal("848076.70")
    assert taot_60_89["percent"] == Decimal("1.04")


def test_em_dash_is_zero():
    """Servicer reports write nil as an em dash. SDART item {76} (121+ days
    delinquent) is nil-count, nil-balance, 0.00% in the June fixture."""
    out = parse_servicer_report(SDART_2026_06_EXCERPT)
    bucket = out["delinquency_buckets"]["121+"]
    assert bucket["count"] == 0
    assert bucket["balance"] == Decimal("0")
    assert bucket["percent"] == Decimal("0.00")


def test_missing_field_raises_not_defaults():
    with pytest.raises(UnparseableServicerReport):
        parse_servicer_report("<html><body>nothing here</body></html>")


def test_unknown_format_raises():
    """A third issuer layout must fail loudly, not silently return zeros."""
    third_issuer_layout = """
    <html><body>
    <p>Monthly Distribution Statement</p>
    <table>
      <tr><td>Pool Principal Balance</td><td>$123,456,789.00</td></tr>
      <tr><td>Delinquency Ratio</td><td>7.50%</td></tr>
    </table>
    </body></html>
    """
    with pytest.raises(UnparseableServicerReport):
        parse_servicer_report(third_issuer_layout)


def test_numbered_values_are_decimal_not_float():
    out = parse_servicer_report(SDART_2026_06_EXCERPT)
    assert isinstance(out["pool_balance"], Decimal)
    assert isinstance(out["delinquency_percent"], Decimal)
    assert isinstance(out["delinquency_buckets"]["31-60"]["balance"], Decimal)


def test_labelled_values_are_decimal_not_float():
    out = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert isinstance(out["pool_balance"], Decimal)
    assert isinstance(out["delinquency_percent"], Decimal)
    assert isinstance(out["delinquency_buckets"]["60-89"]["balance"], Decimal)


def test_both_formats_return_the_same_key_set():
    numbered = parse_servicer_report(SDART_2026_06_EXCERPT)
    labelled = parse_servicer_report(TAOT_2026_06_EXCERPT)
    assert set(numbered) == set(labelled)


def _retag_item_value(stripped: str, item: int, new_value: str) -> str:
    """Replace the value of ONE numbered item, in already-stripped text.

    Operates on the STRIPPED text, because that is the layer the item-zone
    functions work at -- `parse_servicer_report` calls `_strip_html` before
    any of them. Mutating the raw HTML instead rewrites a digit inside the
    markup (`margin-top:0pt`) and corrupts the structure, which is how the
    first version of this probe managed to break both items at once.

    Surgical on purpose: everything outside `{item}`'s value zone is the
    untouched filed text, so the probe changes exactly one thing and nothing
    else can account for the result.
    """
    zone = _item_value_zone(stripped, item)
    tokens = _leading_numeric_tokens(zone)
    assert tokens, f"item {{{item}}} value zone carries no numeric token"

    # Locate the zone by MARKER OFFSET, never by searching for the zone text.
    # `stripped.index(zone)` is wrong here in the most on-the-nose way
    # possible: items {63} and {66} strip down to the byte-identical string
    # '103,857,109.35', so the search resolves to {63} and the probe silently
    # rewrites the wrong item -- which is the exact indistinguishability this
    # test exists to close.
    marker = f"{{{item}}}"
    first = stripped.index(marker)
    second = stripped.index(marker, first + len(marker))
    # Search FORWARD FROM the second marker. The zone is whitespace-stripped,
    # so it does not begin exactly where the marker ends, but it is the first
    # occurrence after it -- and anchoring the search here is what keeps the
    # match unambiguous.
    zone_start = stripped.index(zone, second + len(marker))

    at = zone_start + zone.index(tokens[0])
    return stripped[:at] + new_value + stripped[at + len(tokens[0]):]


def test_oc_amount_and_oc_target_follow_their_own_item_numbers():
    """KNOWN-ISSUES 17.1, CLOSED. A transposed OC field must be detectable.

    `oc_amount` reads numbered item {66} and `oc_target` reads item {63}. In
    every SDART filing loaded those two carry the SAME value -- measured across
    all 36 deal-periods, only one has them differing and it sits in the
    labelled-format oracle -- so the numbered fixtures could not tell a correct
    parser from one with the two item numbers swapped. Both assertions passed
    either way.

    Closed WITHOUT inventing an oracle. The base text is the real June excerpt;
    the probe alters item {66}'s value alone and asserts the two fields diverge
    in the right direction. It tests the MAPPING, which is a property of the
    parser, rather than claiming a filing says something it does not.
    """
    stripped = _strip_html(SDART_2026_06_EXCERPT)
    baseline = _parse_numbered(stripped)
    assert baseline["oc_amount"] == baseline["oc_target"] == Decimal("103857109.35"), (
        "premise of this test: the filed values are equal, which is exactly "
        "why the ordinary fixtures cannot detect a swap")

    probed = _parse_numbered(_retag_item_value(stripped, 66, "99,999,999.99"))

    # {66} moved, so oc_amount must move with it...
    assert probed["oc_amount"] == Decimal("99999999.99")
    # ...and oc_target, which reads {63}, must not have moved at all.
    assert probed["oc_target"] == Decimal("103857109.35")
    assert probed["oc_amount"] != probed["oc_target"]


def test_the_swap_this_probe_exists_to_catch_would_now_fail():
    """The probe is only worth having if a swapped parser fails it.

    Reads the two items the wrong way round and shows the assertions above
    would not hold -- so the probe discriminates, rather than passing because
    everything passes.
    """
    stripped = _strip_html(SDART_2026_06_EXCERPT)
    probed = _retag_item_value(stripped, 66, "99,999,999.99")

    swapped_oc_amount = _numbered_single(probed, 63)   # the wrong item
    swapped_oc_target = _numbered_single(probed, 66)   # the wrong item

    assert swapped_oc_amount != Decimal("99999999.99")
    assert swapped_oc_target != Decimal("103857109.35")
