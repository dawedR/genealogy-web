import sys

from ged4py.parser import GedcomReader


def main(path: str) -> None:
    with GedcomReader(path) as parser:
        print("=== DATES ===")

        count = 0

        for person in parser.records0("INDI"):
            name = person.sub_tag_value("NAME")

            for path_name in (
                "BIRT/DATE",
                "BAPM/DATE",
                "DEAT/DATE",
                "BURI/DATE",
            ):
                date_record = person.sub_tag(path_name)

                if date_record is None:
                    continue

                print()
                print("Personne :", person.xref_id, name)
                print("Chemin   :", path_name)
                print("Record   :", repr(date_record))
                print("Value    :", repr(date_record.value))
                print("Type     :", type(date_record.value).__name__)

                count += 1

                if count >= 20:
                    return


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} fichier.ged")

    main(sys.argv[1])