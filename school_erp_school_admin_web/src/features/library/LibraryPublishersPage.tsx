import {
  deletePublisher,
  listPublishers,
  renamePublisher,
  type PublisherRow,
} from "./api";
import { NameListPage } from "./_name_list";

export function LibraryPublishersPage() {
  return (
    <NameListPage<PublisherRow>
      title="Publishers"
      subtitle="Every publisher whose titles are in the catalogue. Rename to consolidate imprint spellings; delete clears the publisher field on books that carry it."
      queryKey="library-publishers"
      nameField="publisher"
      fetchList={listPublishers}
      renameOne={renamePublisher}
      deleteOne={deletePublisher}
    />
  );
}
