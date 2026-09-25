import sys
import time

from gedcomtools.gedcom5 import Gedcom5


def main(path: str) -> None:
    start = time.perf_counter()

    ged = Gedcom5()
    ged.loadfile(path)

    elapsed = time.perf_counter() - start

    individuals = ged.individuals()
    families = ged.families()

    print(f"Fichier   : {path}")
    print(f"Version   : {ged.detect_gedcom_version()}")
    print(f"Temps     : {elapsed:.4f} s")
    print(f"Individus : {len(individuals)}")
    print(f"Familles  : {len(families)}")

    print()
    print("=== Premier individu ===")

    if not individuals:
        return

    person = individuals[0]

    print("Objet :", repr(person))

    # On utilise l'xref réel exposé par l'objet si possible.
    print()
    print("Attributs publics :")
    for name in dir(person):
        if not name.startswith("_"):
            value = getattr(person, name)
            if not callable(value):
                print(f"  {name} = {value!r}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} fichier.ged")

    main(sys.argv[1])
