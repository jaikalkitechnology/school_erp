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
