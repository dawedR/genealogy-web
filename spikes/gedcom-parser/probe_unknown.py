import sys

from ged4py.parser import GedcomReader


def main(path: str) -> None:
    with GedcomReader(path) as parser:
        person = next(parser.records0("INDI"))

        print("=== Sous-enregistrements de", person.xref_id, "===")

        for record in person.sub_tags(follow=False):
            print(
                f"tag={record.tag!r}",
                f"value={record.value!r}",
                f"type={type(record).__name__}",
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} fichier.ged")

    main(sys.argv[1])
