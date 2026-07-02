import {
  deleteAuthor,
  listAuthors,
  renameAuthor,
  type AuthorRow,
} from "./api";
import { NameListPage } from "./_name_list";

export function LibraryAuthorsPage() {
  return (
    <NameListPage<AuthorRow>
      title="Authors"
      singular="Author"
      subtitle="Every author currently in the catalogue. Rename fixes typos across every book; delete clears the author field on books that carry it."
      queryKey="library-authors"
      fetchList={listAuthors}
      nameOf={(r) => r.author}
      countOf={(r) => r.books}
      renameOne={renameAuthor}
      deleteOne={deleteAuthor}
    />
  );
}
