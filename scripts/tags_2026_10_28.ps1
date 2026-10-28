# tags_2026_10_28.ps1  (2026-10-28)  TAGS_2026_10_28
#
# The edition's own matter typed as such, in two texts (docs\ASKS_2026-10-22.md, section 13):
#   the Hayasirsa: its apparatus of variant readings ("15 maheshvarah-A,B. 16 shirodharam-A,B,C.") as noise: the
#     73 that classify_apparatus.py finds and the 68 more it misses (vision writes the note numbers in its own ways);
#     its title pages and contents (pages 1, 3, 6 and 7) as frontmatter. Page 19, passage 12 is left for a person:
#     half a verse, then the notes. After the tags 1,453 passages are left to translate (1,614 before).
#   the Karanagama: its title pages, its contents, its verse index and its bibliography as frontmatter (pages 1, 3,
#     4, 8, 17 to 25, 153, 155 to 181, and page 12, passage 6); another book's title page (26, 154), the digitizer's
#     stamps (2, 182) and an unreadable page (152) as noise.
# Only text_type changes (classify_apparatus.py, mark_passages.py): the text, the translations and the scholarly
# rows are kept; each change is logged (data\apparatus_tagged_*.json, data\mark_passages_log.jsonl) and --undo puts
# it back. A dry run by default; -Apply writes. From the repository root, with the dashboard idle, after a backup:
#
#   python scripts\db_backup.py data\context.db D:\backups\context_pre_tags_20261028.db
#   powershell -ExecutionPolicy Bypass -File scripts\tags_2026_10_28.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\tags_2026_10_28.ps1 -Apply
param([switch]$Apply)
$H = "HAYASHIRSHA_PANCARATRA"
$K = "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi"
$A = @()
$C = @("--show")
if ($Apply) { $A = @("--apply"); $C = @("--apply") }
$app = "TAGS_2026_10_28: the edition's apparatus of variant readings"
# the Hayasirsa: the apparatus classify_apparatus.py finds (73 on 28 Oct)
python scripts\classify_apparatus.py --doc $H @C
# the Hayasirsa: the apparatus it misses (68), page and passage
$P = @(
    "17 7", "18 11", "20 11", "21 13", "22 11", "23 13", "24 13", "25 11", "27 10", "28 12",
    "29 13", "30 11", "31 10", "34 11", "35 13", "36 11", "37 12", "38 14", "39 11", "40 11",
    "41 12", "42 11", "43 13", "44 13", "45 12", "47 12", "48 11", "49 13", "50 13", "52 12",
    "53 11", "54 12", "55 12", "56 13", "57 17", "58 11", "59 12", "60 12", "63 11", "64 12",
    "65 10", "66 12", "67 12", "68 11", "69 13", "70 12", "71 12", "72 14", "80 12", "86 14",
    "92 11", "100 10", "108 12", "109 12", "114 12", "115 10", "115 12", "117 12", "120 13", "121 11",
    "134 12", "139 14", "140 11", "142 10", "145 9", "146 11", "148 9", "152 11"
)
foreach ($x in $P) {
    $p = $x.Split(" ")
    python scripts\mark_passages.py --doc $H --pages $p[0] --idx $p[1] --type noise --reason $app @A
}
python scripts\mark_passages.py --doc $H --pages "1,3,6,7" --type frontmatter --reason "TAGS_2026_10_28: its title pages and contents" @A
# the Karanagama
python scripts\mark_passages.py --doc $K --pages "1,3,4,8,17-25,153,155-181" --type frontmatter --reason "TAGS_2026_10_28: its title pages, contents, verse index and bibliography" @A
python scripts\mark_passages.py --doc $K --pages 12 --idx 6 --type frontmatter --reason "TAGS_2026_10_28: the publisher's note" @A
python scripts\mark_passages.py --doc $K --pages "2,26,152,154,182" --type noise --reason "TAGS_2026_10_28: another book's title page, the digitizer's stamps, an unreadable page" @A
if (-not $Apply) { Write-Host "TAGS_2026_10_28: a dry run; nothing written. The same with -Apply writes." }
