# Báo cáo Đánh giá Lab 16 Benchmark

**Họ và tên:** Huỳnh Thái Bảo  
**MSSV:** 2A202600373  
**Ngày:** 23/04/2026

## 1. Siêu dữ liệu (Metadata)
- **Dataset**: `hotpot_extra.json`
- **Mode**: `ollama`
- **Records**: 200
- **Agents**: `react`, `reflexion`

## 2. Tóm tắt (Summary)
| Metric | ReAct | Reflexion | Delta (Độ chênh lệch) |
|---|---:|---:|---:|
| Exact Match (EM) | 0.62 | 0.92 | +0.30 |
| Số lần thử trung bình | 1.00 | 1.10 | +0.10 |
| Ước tính token trung bình | 971.34 | 1103.47 | +132.13 |
| Độ trễ trung bình (ms) | 2031.73 | 2832.88 | +801.15 |

## 3. Các dạng lỗi (Failure Modes)
Các dạng lỗi tổng thể được quan sát trong quá trình đánh giá:
- **`wrong_final_answer`**: Xảy ra khi agent đưa ra một thực thể không chính xác hoặc dừng lại giữa chừng (ví dụ: không thực hiện được bước nhảy thứ hai để tìm kiếm thực thể cuối cùng).

Chi tiết theo từng agent:
```json
{
  "react": {
    "none": 62,
    "wrong_final_answer": 38
  },
  "reflexion": {
    "none": 92,
    "wrong_final_answer": 8
  },
  "overall": {
    "none": 154,
    "wrong_final_answer": 46
  }
}
```
Reflexion đã giảm thiểu đáng kể số lượng lỗi `wrong_final_answer` từ 38 xuống còn 8 bằng cách thích ứng chính xác dựa trên các hướng dẫn multi-hop rõ ràng trong những lần thử nghiệm tiếp theo.

## 4. Các tính năng mở rộng đã triển khai
- `structured_evaluator`
- `reflection_memory`
- `benchmark_report_json`
- `mock_mode_for_autograding`

## 5. Thảo luận (Discussion)

**Bộ nhớ Phản xạ (Reflection Memory) hữu ích như thế nào?**
Qua việc so sánh, Reflexion đem lại mức độ cải thiện tuyệt đối rất lớn - 30% về độ chính xác (EM tăng từ 0.62 lên 0.92). Reflection memory đặc biệt hữu ích trong việc giải quyết hai vấn đề chính:
1. **Incomplete Multi-Hopping (Chưa hoàn thành nhảy nhiều bước)**: ReAct thường hay dừng lại ngay ở bước nhảy đầu tiên (ví dụ: tìm ra thành phố nơi sinh nhưng không tiếp tục truy vấn thứ hai để tìm dòng sông chảy qua thành phố đó). Reflexion đã phân tích phản hồi của bộ máy đánh giá (evaluator), nhận ra rằng còn thiếu một thao tác ("Một câu trả lời một phần ở bước nhảy đầu tiên là không đủ"), và từ đó lập chiến lược rõ ràng cho bước nhảy thứ hai ở lượt thử tiếp theo.
2. **Entity Drift (Lệch thực thể)**: Trong vài kịch bản, ReAct truy xuất sai thực thể cuối cùng. Nhờ bộ nhớ phản xạ, Reflexion đã có thể điều chỉnh lại chiến lược ("Xác minh thực thể cuối cùng dựa trên đoạn văn thứ hai trước khi đưa ra câu trả lời").

**Sự đánh đổi (Trade-offs)**
Mức cải tiến hiệu năng lớn cũng đi kèm với một số đánh đổi:
- **Token và Độ trễ**: Reflexion tiêu tốn trung bình nhiều hơn khoảng 13% lượng token (+132.13 tokens mỗi câu truy vấn) và độ trễ tăng khoảng 40% (+801.15 ms) do các bước đánh giá, tự sửa chữa và tạo mẫu bổ sung.
- **Số lần thử**: Số lần thử trung bình chỉ tăng nhẹ lên mức 1.1, cho thấy khả năng tự phục hồi xuất sắc của Reflexion ngay trong chu trình tự sửa chữa đầu tiên thay vì phải dùng hết giới hạn số lần thử.

**Các lỗi vẫn còn tồn đọng & Giới hạn của Evaluator**
Mặc dù Reflexion giải quyết được phần lớn lỗi `wrong_final_answer`, vẫn còn 8% các truy vấn bị đánh fail. Những lỗi còn lại này có thẻ được lý giải do điểm mù/hạn chế cố hữu của chức năng Information Retrieval trong mô hình LLM, hay do hạn chế chất lượng đánh giá. Giả sử evaluator có chẩn đoán sai (false positive) hoặc phê bình quá chung chung, vô tình làm reflection agent không thể xây dựng được một kế hoạch sửa chữa thành công để đối phó. Việc nâng cấp lên mô hình LLM lớn hơn cũng như đưa ra một thang điểm/chỉ tiêu chấm điểm thật chặt chẽ vào `structured_evaluator` chắc chắn sẽ giúp kéo giảm con số thất bại 8% này.