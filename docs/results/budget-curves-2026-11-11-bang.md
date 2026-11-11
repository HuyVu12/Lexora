# Bảng số liệu WP2, WP3 (chạy thử, 11/11/2026)

## Bộ tra cứu (131 câu)

![Bộ tra cứu (131 câu)](budget-curves-2026-11-11-bang-tra-cuu.svg)

Câu hỏi có nhãn: 131.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,56 | 0,56 | 0,74 | 0,81 | 0,85 | 0,92 | 0,94 | 0,98 |
| ĐK2 | 0,72 | 0,82 | 0,88 | 0,91 | 0,92 | 0,95 | 0,96 | 0,97 |
| ĐK3 | 0,64 | 0,76 | 0,84 | 0,88 | 0,91 | 0,94 | 0,95 | 0,96 |
| ĐK4 | 0,65 | 0,75 | 0,83 | 0,87 | 0,91 | 0,93 | 0,95 | 0,96 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,54 | 0,54 | 0,71 | 0,79 | 0,83 | 0,91 | 0,93 | 0,98 |
| ĐK2 | 0,66 | 0,77 | 0,82 | 0,87 | 0,88 | 0,92 | 0,93 | 0,95 |
| ĐK3 | 0,59 | 0,71 | 0,80 | 0,85 | 0,87 | 0,90 | 0,92 | 0,94 |
| ĐK4 | 0,60 | 0,70 | 0,79 | 0,83 | 0,88 | 0,90 | 0,92 | 0,94 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK1 | 263 | 1.228 | 381,3 |
| ĐK2 | 38 | 447 | 45,4 |
| ĐK3 | 47 | 612 | 55,9 |
| ĐK4 | 47 | 632 | 55,3 |

Lượt chạy:

- ĐK1: `experiments/runs/budget-2026-11-11/dryrun-v1-dk1` (đóng gói P0)
- ĐK2: `experiments/runs/budget-2026-11-11/dryrun-v1-dk2` (đóng gói P0)
- ĐK3: `experiments/runs/budget-2026-11-11/dryrun-v1-dk3` (đóng gói P0)
- ĐK4: `experiments/runs/budget-2026-11-11/dryrun-v1-dk4` (đóng gói P0)

## Bộ phức tạp (30 câu)

![Bộ phức tạp (30 câu)](budget-curves-2026-11-11-bang-phuc-tap.svg)

Câu hỏi có nhãn: 30.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,37 | 0,37 | 0,53 | 0,62 | 0,69 | 0,78 | 0,87 | 0,94 |
| ĐK2 | 0,27 | 0,43 | 0,62 | 0,65 | 0,67 | 0,73 | 0,81 | 0,89 |
| ĐK3 | 0,33 | 0,49 | 0,61 | 0,72 | 0,74 | 0,76 | 0,80 | 0,87 |
| ĐK4 | 0,33 | 0,50 | 0,62 | 0,72 | 0,72 | 0,76 | 0,81 | 0,89 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,03 | 0,03 | 0,20 | 0,27 | 0,33 | 0,50 | 0,67 | 0,83 |
| ĐK2 | 0,03 | 0,13 | 0,27 | 0,37 | 0,37 | 0,40 | 0,53 | 0,70 |
| ĐK3 | 0,10 | 0,20 | 0,30 | 0,43 | 0,47 | 0,47 | 0,57 | 0,67 |
| ĐK4 | 0,10 | 0,20 | 0,30 | 0,43 | 0,43 | 0,47 | 0,57 | 0,70 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK1 | 784 | 3.219 | 381,3 |
| ĐK2 | 394 | 3.964 | 45,4 |
| ĐK3 | 323 | 3.954 | 55,9 |
| ĐK4 | 323 | 3.817 | 55,3 |

Lượt chạy:

- ĐK1: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk1` (đóng gói P0)
- ĐK2: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk2` (đóng gói P0)
- ĐK3: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk3` (đóng gói P0)
- ĐK4: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk4` (đóng gói P0)

## Bộ xung đột (25 câu)

![Bộ xung đột (25 câu)](budget-curves-2026-11-11-bang-xung-dot.svg)

Câu hỏi có nhãn: 25.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,19 | 0,19 | 0,29 | 0,39 | 0,47 | 0,54 | 0,59 | 0,64 |
| ĐK2 | 0,13 | 0,21 | 0,35 | 0,39 | 0,43 | 0,52 | 0,58 | 0,62 |
| ĐK3 | 0,11 | 0,20 | 0,26 | 0,35 | 0,43 | 0,52 | 0,56 | 0,62 |
| ĐK4 | 0,11 | 0,21 | 0,26 | 0,35 | 0,43 | 0,52 | 0,55 | 0,62 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,00 | 0,00 | 0,00 | 0,04 | 0,08 | 0,08 | 0,12 | 0,12 |
| ĐK2 | 0,00 | 0,00 | 0,00 | 0,04 | 0,04 | 0,04 | 0,12 | 0,16 |
| ĐK3 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,04 | 0,08 | 0,16 |
| ĐK4 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,04 | 0,08 | 0,16 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK1 | 1.601 | 15.054 | 381,3 |
| ĐK2 | 1.518 | 16.312 | 45,4 |
| ĐK3 | 1.837 | 18.938 | 55,9 |
| ĐK4 | 1.839 | 18.378 | 55,3 |

Lượt chạy:

- ĐK1: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk1` (đóng gói P0)
- ĐK2: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk2` (đóng gói P0)
- ĐK3: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk3` (đóng gói P0)
- ĐK4: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk4` (đóng gói P0)

## Bộ tình huống (44 câu)

![Bộ tình huống (44 câu)](budget-curves-2026-11-11-bang-tinh-huong.svg)

Câu hỏi có nhãn: 44.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,12 | 0,12 | 0,25 | 0,33 | 0,42 | 0,48 | 0,58 | 0,66 |
| ĐK2 | 0,08 | 0,16 | 0,25 | 0,29 | 0,33 | 0,42 | 0,47 | 0,53 |
| ĐK3 | 0,08 | 0,15 | 0,27 | 0,33 | 0,37 | 0,42 | 0,48 | 0,52 |
| ĐK4 | 0,08 | 0,16 | 0,29 | 0,34 | 0,37 | 0,43 | 0,48 | 0,53 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK1 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,02 | 0,07 | 0,16 |
| ĐK2 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,02 | 0,05 |
| ĐK3 | 0,00 | 0,00 | 0,00 | 0,02 | 0,02 | 0,02 | 0,02 | 0,02 |
| ĐK4 | 0,00 | 0,00 | 0,00 | 0,02 | 0,02 | 0,02 | 0,02 | 0,05 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK1 | 1.628 | 17.208 | 381,3 |
| ĐK2 | 2.598 | - | 45,4 |
| ĐK3 | 2.304 | - | 55,9 |
| ĐK4 | 2.304 | - | 55,3 |

Lượt chạy:

- ĐK1: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk1` (đóng gói P0)
- ĐK2: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk2` (đóng gói P0)
- ĐK3: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk3` (đóng gói P0)
- ĐK4: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk4` (đóng gói P0)

## Đóng gói ĐK2, bộ phức tạp

![Đóng gói ĐK2, bộ phức tạp](budget-curves-2026-11-11-bang-dong-goi-phuc-tap.svg)

Câu hỏi có nhãn: 30.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,27 | 0,43 | 0,62 | 0,65 | 0,67 | 0,73 | 0,81 | 0,89 |
| ĐK2-P1 | 0,31 | 0,49 | 0,63 | 0,65 | 0,70 | 0,78 | 0,82 | 0,90 |
| ĐK2-P2 | 0,29 | 0,46 | 0,66 | 0,69 | 0,71 | 0,79 | 0,83 | 0,91 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,03 | 0,13 | 0,27 | 0,37 | 0,37 | 0,40 | 0,53 | 0,70 |
| ĐK2-P1 | 0,07 | 0,13 | 0,30 | 0,37 | 0,37 | 0,47 | 0,57 | 0,73 |
| ĐK2-P2 | 0,00 | 0,13 | 0,33 | 0,43 | 0,43 | 0,50 | 0,57 | 0,73 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK2-P0 | 394 | 3.964 | 45,4 |
| ĐK2-P1 | 372 | 3.689 | 45,4 |
| ĐK2-P2 | 348 | 3.061 | 45,4 |

Lượt chạy:

- ĐK2-P0: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk2` (đóng gói P0)
- ĐK2-P1: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk2-P1` (đóng gói P1)
- ĐK2-P2: `experiments/runs/budget-2026-11-11/dryrun-complex-v1-dk2-P2` (đóng gói P2)

## Đóng gói ĐK2, bộ xung đột

![Đóng gói ĐK2, bộ xung đột](budget-curves-2026-11-11-bang-dong-goi-xung-dot.svg)

Câu hỏi có nhãn: 25.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,13 | 0,21 | 0,35 | 0,39 | 0,43 | 0,52 | 0,58 | 0,62 |
| ĐK2-P1 | 0,14 | 0,24 | 0,37 | 0,42 | 0,46 | 0,54 | 0,60 | 0,66 |
| ĐK2-P2 | 0,11 | 0,24 | 0,37 | 0,44 | 0,48 | 0,54 | 0,61 | 0,66 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,00 | 0,00 | 0,00 | 0,04 | 0,04 | 0,04 | 0,12 | 0,16 |
| ĐK2-P1 | 0,00 | 0,00 | 0,00 | 0,04 | 0,04 | 0,04 | 0,16 | 0,28 |
| ĐK2-P2 | 0,00 | 0,00 | 0,04 | 0,04 | 0,04 | 0,08 | 0,16 | 0,28 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK2-P0 | 1.518 | 16.312 | 45,4 |
| ĐK2-P1 | 1.246 | 11.897 | 45,4 |
| ĐK2-P2 | 1.161 | 10.806 | 45,4 |

Lượt chạy:

- ĐK2-P0: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk2` (đóng gói P0)
- ĐK2-P1: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk2-P1` (đóng gói P1)
- ĐK2-P2: `experiments/runs/budget-2026-11-11/dryrun-conflict-v1-dk2-P2` (đóng gói P2)

## Đóng gói ĐK2, bộ tình huống

![Đóng gói ĐK2, bộ tình huống](budget-curves-2026-11-11-bang-dong-goi-tinh-huong.svg)

Câu hỏi có nhãn: 44.

Recall trung bình theo ngân sách token:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,08 | 0,16 | 0,25 | 0,29 | 0,33 | 0,42 | 0,47 | 0,53 |
| ĐK2-P1 | 0,08 | 0,16 | 0,25 | 0,31 | 0,38 | 0,46 | 0,49 | 0,57 |
| ĐK2-P2 | 0,07 | 0,14 | 0,26 | 0,35 | 0,41 | 0,48 | 0,53 | 0,59 |

Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:

| Điều kiện | 250 | 500 | 1.000 | 1.500 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|---|---|
| ĐK2-P0 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,02 | 0,05 |
| ĐK2-P1 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,02 | 0,05 | 0,07 |
| ĐK2-P2 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,02 | 0,07 |

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):

| Điều kiện | recall 0,4 | recall 0,8 | Token trung bình mỗi bản ghi |
|---|---|---|---|
| ĐK2-P0 | 2.598 | - | 45,4 |
| ĐK2-P1 | 2.268 | - | 45,4 |
| ĐK2-P2 | 1.959 | - | 45,4 |

Lượt chạy:

- ĐK2-P0: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk2` (đóng gói P0)
- ĐK2-P1: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk2-P1` (đóng gói P1)
- ĐK2-P2: `experiments/runs/budget-2026-11-11/dryrun-cases-v1-dk2-P2` (đóng gói P2)
