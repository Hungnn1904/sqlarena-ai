'use client';

import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Cpu,
  ShieldCheck,
  Wrench,
  XCircle,
} from 'lucide-react';

const PIPELINE_STEPS = [
  { id: 1, short: '1. Model A', full: 'Model A: Sinh đề bài & Chữ ký logic' },
  { id: 2, short: '2. Validator', full: 'Validator: Kiểm tra Schema, Độ khó & Trùng đề' },
  { id: 3, short: '3. Model B', full: 'Model B: Giải đề độc lập (Blind Solving)' },
  { id: 4, short: '4. Đồng thuận', full: 'Thực thi PostgreSQL 17 & Kiểm tra đồng thuận' },
  { id: 5, short: '5. Kiểm toán', full: 'Kiểm toán ngữ nghĩa & Chốt Test Cases' },
];

function formatVerdictLabel(status?: string | null): { text: string; cls: string } {
  switch (status) {
    case 'approved':
      return { text: 'Approved · Đã duyệt', cls: 'badge-easy' };
    case 'needs_human':
      return { text: 'Needs Human · Cần duyệt tay', cls: 'badge-medium' };
    case 'rejected':
      return { text: 'Rejected · Từ chối', cls: 'badge-hard' };
    default:
      return { text: 'Đang kiểm định AI', cls: 'badge-info' };
  }
}

export function JobActivePipelineBanner({
  job,
  elapsedSec,
  activeModel,
}: {
  job: any;
  elapsedSec: number;
  activeModel?: string | null;
}) {
  if (!job) return null;
  const isFailed = job.status === 'failed';
  const isRunning = job.status === 'running' || job.status === 'queued';
  if (!isRunning && !isFailed) return null;

  return (
    <div className="px-4 py-3 bg-canvas border-b border-line space-y-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-ink tabular-nums">
          {isFailed
            ? `Đợt sinh đề #${job.job_id} dừng do sự cố (${job.created_count ?? 0}/${job.requested_count ?? 0} câu)`
            : `Đang chạy Đợt #${job.job_id}: đã sinh ${job.created_count ?? 0}/${job.requested_count ?? 0} câu`}
        </span>
        <div className="flex flex-wrap items-center gap-1.5 tabular-nums">
          {activeModel && (
            <span className="badge-neutral px-2 py-0.5 rounded font-semibold inline-flex items-center gap-1">
              <Cpu className="w-3 h-3" />
              <span>{activeModel}</span>
            </span>
          )}
          {isRunning && (
            <span className="badge-info px-2 py-0.5 rounded font-semibold inline-flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>Đang chạy: {elapsedSec}s</span>
            </span>
          )}
        </div>
      </div>

      {isRunning && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
          {PIPELINE_STEPS.map((st) => {
            const active = st.id === 1;
            return (
              <div
                key={st.id}
                title={st.full}
                className={`px-2 py-1 rounded border text-[11px] font-semibold truncate ${
                  active ? 'badge-info border-transparent' : 'bg-surface border-line text-muted'
                }`}
              >
                {st.short}
              </div>
            );
          })}
        </div>
      )}

      {job.error_message && (
        <div className="px-2.5 py-1.5 rounded-lg badge-hard font-medium flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>{String(job.error_message)}</span>
        </div>
      )}
    </div>
  );
}

export function DraftPipelineRowProgress({ draft }: { draft: any }) {
  const lp = draft?.live_progress;
  if (!lp) return null;

  const currentStep = Number(lp.step || 2);
  const isRunning = Boolean(lp.is_running);
  const isApproved = draft.status === 'approved';
  const isRejected = draft.status === 'rejected';
  const isNeedsHuman = draft.status === 'needs_human';

  return (
    <div className="pt-1.5 space-y-1.5">
      {/* 5-Stage Pipeline Stepper */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-1">
        {PIPELINE_STEPS.map((st) => {
          const done = currentStep > st.id || (!isRunning && currentStep >= st.id && isApproved);
          const current = currentStep === st.id && (isRunning || !isApproved);
          let cls = 'bg-canvas border-line text-muted';
          if (done) {
            cls = 'badge-easy border-transparent';
          } else if (current) {
            if (isRejected) cls = 'badge-hard border-transparent';
            else if (isNeedsHuman) cls = 'badge-medium border-transparent';
            else cls = 'badge-info border-transparent';
          }
          return (
            <div
              key={st.id}
              title={st.full}
              className={`px-2 py-1 rounded border text-[11px] font-semibold truncate ${cls}`}
            >
              {st.short}
            </div>
          );
        })}
      </div>

      {/* Sub-step Live Telemetry Chips */}
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-text2 tabular-nums">
        <span className="font-medium text-ink">{lp.step_label}</span>
        <span>·</span>
        <span>
          {lp.active_sample
            ? `Mẫu đang giải: ${lp.active_sample}/${lp.samples_total || 3}`
            : `Mẫu giải: ${lp.samples_done ?? 0}/${lp.samples_total || 3}`}
        </span>
        {lp.active_model && (
          <>
            <span>·</span>
            <span className="inline-flex items-center gap-1 font-semibold text-ink">
              <Cpu className="w-3 h-3 text-brand" />
              <span>{lp.active_model}</span>
            </span>
          </>
        )}
        {lp.elapsed_seconds !== null && lp.elapsed_seconds !== undefined && (
          <>
            <span>·</span>
            <span>
              {isRunning ? `Đang chạy: ${lp.elapsed_seconds}s` : `Thời gian: ${lp.elapsed_seconds}s`}
            </span>
          </>
        )}
        {Number(lp.repair_round || 0) > 0 && (
          <span className="badge-medium px-1.5 py-0.5 rounded font-semibold inline-flex items-center gap-1">
            <Wrench className="w-3 h-3" />
            <span>
              {isRunning
                ? `Đang tự sửa SQL vòng ${lp.repair_round}/${lp.max_repair_rounds || 2}`
                : `Đã tự sửa vòng ${lp.repair_round}/${lp.max_repair_rounds || 2}`}
            </span>
          </span>
        )}
      </div>

      {/* Inline Error Alert */}
      {lp.error_alert && (
        <div className="px-2.5 py-1.5 rounded-lg badge-hard text-[11px] font-semibold flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>{lp.error_alert}</span>
        </div>
      )}
    </div>
  );
}

export function DraftAcceptanceDossier({
  dossier,
  onSelectRunSql,
}: {
  dossier: any;
  onSelectRunSql?: (runId: number, sql: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  if (!dossier) return null;

  const verdict = dossier.verdict || {};
  const orig = dossier.originality || {};
  const cons = dossier.consensus || {};
  const checklist: any[] = Array.isArray(dossier.checklist) ? dossier.checklist : [];
  const rt = dossier.repair_and_traps || {};
  const repair = rt.repair_history || { attempted: 0, limit: 2, rounds: [] };
  const traps: string[] = Array.isArray(rt.traps) ? rt.traps : [];
  const vBadge = formatVerdictLabel(verdict.status);
  const passedChecks = checklist.filter((c) => c.passed).length;

  return (
    <div className="rounded-xl border border-line bg-canvas overflow-hidden">
      {/* Header Bar with Collapse Toggle */}
      <div className="px-4 py-3 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-brand shrink-0" />
          <span className="text-sm font-bold text-ink">
            Hồ sơ đánh giá nghiệm thu &amp; chất lượng đề AI
          </span>
          <span className="badge-neutral px-2 py-0.5 rounded text-xs font-semibold tabular-nums">
            {passedChecks}/{checklist.length || 6} tiêu chí đạt
          </span>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className="btn-secondary px-2.5 min-h-7 rounded-md text-xs font-semibold inline-flex items-center gap-1 whitespace-nowrap"
        >
          <span>{expanded ? 'Thu gọn hồ sơ' : 'Mở chi tiết 5 khối'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Block 1 Always Visible: Final Decision & Verdict */}
      <div className="p-4 space-y-3 divide-y divide-line">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-bold text-ink">
              1. Kết luận thẩm định
            </span>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${vBadge.cls}`}>
                {vBadge.text}
              </span>
              <span className="badge-neutral px-2 py-0.5 rounded text-xs font-semibold">
                So khớp: {verdict.compare_mode === 'ordered' ? 'ordered (đúng thứ tự dòng)' : 'unordered (tập hợp bản ghi)'}
              </span>
            </div>
          </div>
          <div className="text-xs text-ink leading-relaxed bg-surface p-2.5 rounded-lg border border-line">
            <span className="font-semibold">Lý do quyết định: </span>
            <span>{verdict.reason_summary}</span>
          </div>
        </div>

        {expanded && (
          <>
            {/* Block 2: Originality & Anti-Duplicate */}
            <div className="pt-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-ink">
                  2. Chỉ số độc bản &amp; Chống trùng đề
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-semibold tabular-nums ${
                    orig.suspected_duplicate ? 'badge-hard' : 'badge-easy'
                  }`}
                >
                  {orig.suspected_duplicate ? 'Cảnh báo nghi trùng' : `Độ độc bản: ${orig.originality_pct ?? 100}%`}
                </span>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs text-text2 tabular-nums">
                  <span>Độ tương đồng văn bản (TF-IDF): {orig.similarity_pct ?? 0}%</span>
                  <span>Độ độc bản: {orig.originality_pct ?? 100}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-soft overflow-hidden border border-line">
                  <div
                    className="h-full bg-[var(--green)]"
                    style={{ width: `${Math.max(4, Math.min(100, Number(orig.originality_pct ?? 100)))}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div className="p-2 rounded-lg bg-surface border border-line">
                  <div className="text-muted">Câu gần giống nhất</div>
                  <div className="font-semibold text-ink mt-0.5 tabular-nums">
                    {orig.nearest_id ? `${orig.nearest_id} (${orig.similarity_pct ?? 0}%)` : 'Không có bản ghi gần'}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-surface border border-line">
                  <div className="text-muted">Trùng lặp câu chữ</div>
                  <div className="font-semibold text-ink mt-0.5">
                    {orig.exact_duplicate ? 'Có (Cần viết lại)' : 'Không'}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-surface border border-line">
                  <div className="text-muted">Trùng bản chất logic</div>
                  <div className="font-semibold text-ink mt-0.5">
                    {orig.logic_duplicate ? 'Có (Trùng chữ ký logic)' : 'Không (Chữ ký logic mới)'}
                  </div>
                </div>
              </div>
            </div>

            {/* Block 3: Model B Consensus & SQL Matrix */}
            <div className="pt-3 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-ink">
                  3. Chỉ số đồng thuận &amp; Đối chiếu lời giải Model B
                </span>
                <span className="badge-info px-2 py-0.5 rounded text-xs font-semibold tabular-nums">
                  Đồng thuận: {cons.matching_count ?? 0}/{cons.total_samples ?? 0} mẫu ({cons.consensus_pct ?? 0}%)
                </span>
              </div>

              <div className="w-full h-2 rounded-full bg-soft overflow-hidden border border-line">
                <div
                  className="h-full bg-[var(--green)]"
                  style={{ width: `${Math.max(0, Math.min(100, Number(cons.consensus_pct ?? 0)))}%` }}
                />
              </div>

              {(cons.samples || []).length > 0 ? (
                <div className="overflow-x-auto rounded-lg border border-line bg-surface">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-soft border-b border-line text-muted">
                        <th className="p-2.5 font-semibold">Mẫu &amp; Câu lệnh SQL</th>
                        <th className="p-2.5 font-semibold whitespace-nowrap">Thực thi PG17</th>
                        <th className="p-2.5 font-semibold whitespace-nowrap">Số dòng &amp; Mã băm</th>
                        <th className="p-2.5 font-semibold whitespace-nowrap">Vai trò đáp án</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line align-top">
                      {(cons.samples as any[]).map((s: any) => (
                        <tr key={s.run_id ?? s.sample_index}>
                          <td className="p-2.5 min-w-[220px] max-w-[340px] space-y-1">
                            <div className="font-semibold text-ink">{s.sample_label}</div>
                            {s.model_sql ? (
                              <pre className="p-2 rounded bg-canvas border border-line font-mono text-[11px] text-ink whitespace-pre-wrap break-words">
                                {s.model_sql}
                              </pre>
                            ) : (
                              <span className="text-muted">Không sinh được SQL hợp lệ</span>
                            )}
                            {s.error && <div className="text-[11px] text-[var(--danger)]">{s.error}</div>}
                          </td>
                          <td className="p-2.5 whitespace-nowrap tabular-nums space-y-1">
                            <span
                              className={`px-2 py-0.5 rounded font-semibold inline-block ${
                                s.exec_status === 'ok' ? 'badge-easy' : 'badge-hard'
                              }`}
                            >
                              {s.exec_status}
                            </span>
                            {s.latency_ms !== null && s.latency_ms !== undefined && (
                              <div className="text-muted">{s.latency_ms} ms</div>
                            )}
                          </td>
                          <td className="p-2.5 whitespace-nowrap tabular-nums space-y-1">
                            <div className="font-semibold text-ink">{s.row_count ?? 0} dòng</div>
                            {s.result_hash && (
                              <code className="font-mono text-[11px] text-muted block">
                                {String(s.result_hash).slice(0, 10)}
                              </code>
                            )}
                          </td>
                          <td className="p-2.5 space-y-1.5">
                            {s.is_selected ? (
                              <div className="space-y-1">
                                <span className="badge-easy px-2 py-0.5 rounded font-semibold inline-block whitespace-nowrap">
                                  Đáp án chuẩn
                                </span>
                                <div className="text-[11px] text-text2 leading-snug">
                                  {s.selection_reason}
                                </div>
                              </div>
                            ) : s.run_id && s.model_sql && onSelectRunSql ? (
                              <button
                                type="button"
                                onClick={() => onSelectRunSql(s.run_id, s.model_sql)}
                                className="btn-secondary px-2.5 min-h-7 rounded text-[11px] font-semibold whitespace-nowrap"
                              >
                                Dùng câu SQL này
                              </button>
                            ) : (
                              <span className="text-muted">Mẫu đối chiếu</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-surface border border-line text-xs text-muted">
                  Bản nháp sử dụng đáp án chuẩn trực tiếp (không có bản ghi giải chéo).
                </div>
              )}
            </div>

            {/* Block 4: 6-Point Semantic & Rule Checklist */}
            <div className="pt-3 space-y-2">
              <span className="text-xs font-bold text-ink block">
                4. Bảng kiểm toán ngữ nghĩa &amp; Luật bài toán
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {checklist.map((item: any) => (
                  <div
                    key={item.key}
                    className="p-2.5 rounded-lg bg-surface border border-line flex items-start gap-2 text-xs"
                  >
                    {item.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-[var(--green)] shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-4 h-4 text-[var(--danger)] shrink-0 mt-0.5" />
                    )}
                    <div className="min-w-0">
                      <div className="font-semibold text-ink">{item.label}</div>
                      <div className="text-muted text-[11px] leading-snug mt-0.5">{item.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Block 5: Repair History & Pedagogical Traps */}
            <div className="pt-3 space-y-2.5">
              <span className="text-xs font-bold text-ink block">
                5. Nhật ký tự sửa lỗi &amp; Điểm lưu ý nghiệp vụ
              </span>

              <div className="p-2.5 rounded-lg bg-surface border border-line space-y-1.5 text-xs">
                <div className="font-semibold text-ink">
                  Lịch sử tự sửa lỗi (Repair History):{' '}
                  {Number(repair.attempted || 0) > 0
                    ? `Đã tự sửa ${repair.attempted}/${repair.limit || 2} vòng`
                    : 'Đạt ngay từ vòng đầu (0 vòng tự sửa)'}
                </div>
                {(repair.rounds || []).map((rd: any) => (
                  <div key={rd.round} className="pl-2 border-l-2 border-line text-[11px] text-text2 space-y-0.5">
                    <div className="font-semibold text-ink">
                      Vòng {rd.round}/{repair.limit || 2} · Kết quả: {rd.outcome}
                    </div>
                    <div>
                      Lỗi phát hiện trước khi sửa:{' '}
                      {(rd.prior_reasons || []).map((r: any) => `${r.code} (${r.explanation})`).join('; ') || 'Không rõ'}
                    </div>
                  </div>
                ))}
              </div>

              {traps.length > 0 && (
                <div className="p-2.5 rounded-lg bg-surface border border-line space-y-1 text-xs">
                  <div className="font-semibold text-ink">Bẫy nghiệp vụ &amp; điểm dễ sai của đề bài:</div>
                  <ul className="list-disc pl-4 space-y-1 text-text2">
                    {traps.map((tr, i) => (
                      <li key={i}>{tr}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
