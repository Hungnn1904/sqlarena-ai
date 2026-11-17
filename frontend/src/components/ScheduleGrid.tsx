'use client';

import React from 'react';

interface ScheduleItem {
  time: string;
  description: React.ReactNode;
}

const items: ScheduleItem[] = [
  {
    time: 'Chủ nhật 22:00',
    description: 'Chạy tiến trình sinh câu hỏi nháp theo nhóm kỹ năng cho tuần tiếp theo.',
  },
  {
    time: 'Thứ hai sáng',
    description: 'Giảng viên rà soát hàng đợi nháp, gom vào nhóm đề và phát hành lên kệ.',
  },
  {
    time: 'Thứ hai 08:00',
    description: 'Bộ đề mới mở chính thức cho sinh viên thực hành và nộp bài chấm tự động.',
  },
  {
    time: 'Trong tuần',
    description: 'Hệ thống thống kê tỷ lệ giải đúng theo từng kỹ năng để cân bằng đợt đề kế tiếp.',
  },
];

export default function ScheduleGrid() {
  return (
    <div className="bg-surface border border-line rounded-xl overflow-hidden my-6 divide-y divide-line">
      {items.map((item, i) => (
        <div key={i} className="grid grid-cols-1 sm:grid-cols-[160px_1fr]">
          <div className="px-4 py-3.5 text-sm font-semibold text-brand bg-soft sm:border-r border-line">
            {item.time}
          </div>
          <div className="px-4 py-3.5 text-sm text-text2">
            {item.description}
          </div>
        </div>
      ))}
    </div>
  );
}
