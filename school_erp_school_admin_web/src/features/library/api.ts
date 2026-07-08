import { api } from "@/lib/api";

export type BorrowerKind = "student" | "teacher";
export type CopyStatus = "available" | "issued" | "reserved" | "lost" | "damaged";
export type LoanStatus = "active" | "returned" | "overdue" | "lost";
export type ReservationStatus = "pending" | "ready" | "fulfilled" | "cancelled";

export interface Book {
  id: number;
  isbn: string | null;
  title: string;
  author: string | null;
  publisher: string | null;
  edition: string | null;
  category: string | null;
  language: string | null;
  cover_path: string | null;
  description: string | null;
  default_fine_per_day: number;
  default_loan_days: number;
  total_copies: number;
  available_copies: number;
}

export interface Copy {
  id: number;
  book_id: number;
  barcode: string;
  accession_number: string | null;
  status: CopyStatus;
  notes: string | null;
}

export interface Loan {
  id: number;
  copy_id: number;
  book_id: number;
  borrower_kind: BorrowerKind;
  borrower_id: number;
  issued_on: string;
  due_on: string;
  returned_on: string | null;
  status: LoanStatus;
  fine_amount: number;
  fine_paid: number;
}

export interface Reservation {
  id: number;
  book_id: number;
  borrower_kind: BorrowerKind;
  borrower_id: number;
  requested_at: string;
  ready_at: string | null;
  fulfilled_at: string | null;
  cancelled_at: string | null;
  status: ReservationStatus;
}

export interface Reports {
  total_books: number;
  total_copies: number;
  issued: number;
  overdue: number;
  available: number;
  fines_outstanding: number;
  by_category: { category: string | null; books: number; copies: number }[];
}

const base = "/v1/school-admin/library";

export const listBooks = async (params: { q?: string; category?: string } = {}) =>
  (await api.get<Book[]>(`${base}/books`, { params })).data;

export const createBook = async (p: Partial<Book> & { title: string }) =>
  (await api.post<Book>(`${base}/books`, p)).data;

export const updateBook = async (id: number, p: Partial<Book> & { title: string }) =>
  (await api.patch<Book>(`${base}/books/${id}`, p)).data;

export const deleteBook = async (id: number) =>
  (await api.delete(`${base}/books/${id}`)).data;

export const listCopies = async (bookId: number) =>
  (await api.get<Copy[]>(`${base}/books/${bookId}/copies`)).data;

export const addCopy = async (
  bookId: number,
  p: { barcode: string; accession_number?: string; notes?: string },
) => (await api.post<Copy>(`${base}/books/${bookId}/copies`, p)).data;

export const addCopiesBulk = async (
  bookId: number,
  p: { count: number; barcode_prefix?: string; accession_prefix?: string },
) => (await api.post<Copy[]>(`${base}/books/${bookId}/copies/bulk`, p)).data;

export const issueLoan = async (p: {
  copy_id: number;
  borrower_kind: BorrowerKind;
  borrower_id: number;
  loan_days?: number;
}) => (await api.post<Loan>(`${base}/issue`, p)).data;

export const returnLoan = async (p: {
  loan_id: number;
  on_date?: string;
  fine_paid?: number;
  mark_lost?: boolean;
}) => (await api.post<Loan>(`${base}/return`, p)).data;

export const listLoans = async (params: {
  status_filter?: LoanStatus;
  borrower_kind?: BorrowerKind;
  borrower_id?: number;
} = {}) => (await api.get<Loan[]>(`${base}/loans`, { params })).data;

export const sweepOverdue = async () =>
  (await api.post<{ marked_overdue: number }>(`${base}/sweep-overdue`)).data;

export const listReservations = async (params: { status_filter?: ReservationStatus } = {}) =>
  (await api.get<Reservation[]>(`${base}/reservations`, { params })).data;

export const createReservation = async (p: {
  book_id: number;
  borrower_kind: BorrowerKind;
  borrower_id: number;
}) => (await api.post<Reservation>(`${base}/reservations`, p)).data;

export const cancelReservation = async (id: number) =>
  (await api.post<Reservation>(`${base}/reservations/${id}/cancel`)).data;

export const reports = async () => (await api.get<Reports>(`${base}/reports`)).data;

export const renameCategory = async (from: string, to: string) =>
  (await api.post<{ updated: number; from: string; to: string }>(
    `${base}/categories/rename`,
    { from, to },
  )).data;

export const deleteCategory = async (name: string) =>
  (await api.delete<{ cleared: number; category: string }>(
    `${base}/categories/${encodeURIComponent(name)}`,
  )).data;

// --- Authors --------------------------------------------------------------

export interface AuthorRow { author: string; books: number }

export const listAuthors = async () =>
  (await api.get<AuthorRow[]>(`${base}/authors`)).data;

export const renameAuthor = async (from: string, to: string) =>
  (await api.post<{ updated: number; from: string; to: string }>(
    `${base}/authors/rename`, { from, to },
  )).data;

export const deleteAuthor = async (name: string) =>
  (await api.delete<{ cleared: number; author: string }>(
    `${base}/authors/${encodeURIComponent(name)}`,
  )).data;

// --- Publishers -----------------------------------------------------------

export interface PublisherRow { publisher: string; books: number }

export const listPublishers = async () =>
  (await api.get<PublisherRow[]>(`${base}/publishers`)).data;

export const renamePublisher = async (from: string, to: string) =>
  (await api.post<{ updated: number; from: string; to: string }>(
    `${base}/publishers/rename`, { from, to },
  )).data;

export const deletePublisher = async (name: string) =>
  (await api.delete<{ cleared: number; publisher: string }>(
    `${base}/publishers/${encodeURIComponent(name)}`,
  )).data;

// --- Renew a loan ---------------------------------------------------------

export const renewLoan = async (loanId: number, extraDays: number) =>
  (await api.post<{ loan_id: number; new_due_on: string }>(
    `${base}/loans/${loanId}/renew`, { extra_days: extraDays },
  )).data;

// --- Recent activity (audit-lite) -----------------------------------------

export interface ActivityEvent {
  kind: "issue" | "return" | "book_created" | "copy_created";
  when: string | null;
  loan_id?: number;
  copy_id?: number;
  book_id?: number;
  title?: string;
  barcode?: string;
  borrower_kind?: BorrowerKind;
  borrower_id?: number;
  fine_paid?: number;
}

export const recentActivity = async (limit = 100) =>
  (await api.get<ActivityEvent[]>(`${base}/activity`, { params: { limit } })).data;

// --- Notification templates -----------------------------------------------

export type NotifChannel = "in_app" | "push" | "sms" | "email" | "whatsapp";

export interface LibraryTemplate {
  code: string;
  subject_en: string;
  body_en: string;
  channels: NotifChannel[];
  is_active: boolean;
}

export const listLibraryTemplates = async () =>
  (await api.get<LibraryTemplate[]>(`${base}/notification-templates`)).data;

export const updateLibraryTemplate = async (
  code: string,
  patch: Partial<Pick<LibraryTemplate, "subject_en" | "body_en" | "channels" | "is_active">>,
) =>
  (await api.put<LibraryTemplate>(`${base}/notification-templates/${encodeURIComponent(code)}`, patch)).data;

// --- Diagnostics + test send ---------------------------------------------

export interface NotifDiagnostics {
  tenant_id: number;
  templates_seeded: number;
  templates_expected: number;
  templates: Record<string, { seeded: boolean; active: boolean; channels: string[] }>;
  borrower?: {
    kind: string;
    id: number;
    recipient_count: number;
    recipients: {
      user_id: number;
      name: string;
      email: string | null;
      phone: string | null;
      is_active: boolean;
      active_devices: number;
    }[];
    recent_outbox_rows: {
      id: number;
      recipient_user_id: number;
      channel: string;
      status: string;
      subject: string | null;
      error: string | null;
      created_at: string | null;
    }[];
  };
}

export const notificationDiagnostics = async (
  borrower?: { kind: "student" | "teacher"; id: number },
) =>
  (await api.get<NotifDiagnostics>(`${base}/notifications/diagnostics`, {
    params: borrower ? { borrower_kind: borrower.kind, borrower_id: borrower.id } : undefined,
  })).data;

export interface TestSendResult {
  ok: boolean;
  reason?: string;
  recipient_count: number;
  recipients?: { user_id: number; name: string }[];
  in_app_created?: number;
  push_outbox_queued?: number;
  push_result?: { sent: number; failed: number } | null;
}

export const notificationTestSend = async (kind: "student" | "teacher", id: number) =>
  (await api.post<TestSendResult>(`${base}/notifications/test-send`, {
    borrower_kind: kind, borrower_id: id,
  })).data;

// --- Borrower search picker (students / teachers) ------------------------

export interface BorrowerRow {
  id: number;
  name: string;
  hint: string;
}

export const borrowerSearch = async (
  kind: "student" | "teacher", q: string, limit = 20,
) =>
  (await api.get<BorrowerRow[]>(`${base}/borrowers/search`, {
    params: { kind, q, limit },
  })).data;
