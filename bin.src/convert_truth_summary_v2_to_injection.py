import argparse
import logging

import lsst.daf.butler as dafButler
from lsst.daf.butler.formatters.parquet import astropy_to_arrow, pq
from lsst.sitcom.sciunit.galaxies.truth_summary import convert_truth_summary_v2_to_injection


"""
Note that the following were used for DP1 A360:
tracts = ((3828, 10463), (3829, 10464), (3828, 10704))
... and ECDFS:
tracts = ((3828, 5063), (3828, 4848), (3829, 4849))
... with n_skip_extended=1.
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser("make_dp2_paper_plots")
    parser.add_argument(
        "tracts_out",
        help="Comma-separated list of colon-separated pairs of input:output tract number,"
             " e.g. 5063:3828,5064:3829.",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--bands",
        help="Comma-separated list of bands",
        type=str,
        default="u,g,r,i,z,y",
    )
    parser.add_argument(
        "--butler_in",
        help="Name of or path to DC2 butler",
        type=str,
        default="dc2",
    )
    parser.add_argument(
        "--butler_out",
        help="Name of or path to butler with output skymap",
        type=str,
        default="dp2_prep",
    )
    parser.add_argument(
        "--collection_out",
        help="Name of collection in output butler with a coadd-level processing run."
             "Only needed if --plot is set.",
        type=str,
        default="LSSTCam/runs/DRP/DP2",
    )
    parser.add_argument("--log_level", help="Logging level", type=str, default="INFO")
    parser.add_argument(
        "--mag_total_min_star",
        help="Minimum magnitude below which bright stars are excluded",
        type=float,
        default=16.5,
    )
    parser.add_argument(
        "--mag_total_min_galaxy",
        help="Minimum magnitude below which bright galaxies are excluded",
        type=float,
        default=16.5,
    )
    parser.add_argument(
        "--mag_total_max",
        help="Minimum magnitude below which bright galaxies are excluded",
        type=float,
        default=26.5,
    )
    parser.add_argument(
        "--n_skip_psf",
        help="Number of unresolved objects to skip before the next exclusion, i.e. a value of N will select"
             " only every N+1 stars.",
        type=float,
        default=0.,
    )
    parser.add_argument(
        "--n_skip_extended",
        help="Number of resolved objects to skip before the next exclusion, i.e. a value of N will select"
             " only every N+1 galaxies.",
        type=float,
        default=7.,
    )
    parser.add_argument("--plot", help="Make and show plots interactively", action="store_true")
    parser.add_argument(
        "--skymap_name_in",
        help="Name of the input skymap.",
        type=str,
        default="DC2_cells_v1",
    )
    parser.add_argument(
        "--skymap_name_out",
        help="Name of the output skymap.",
        type=str,
        default="lsst_cells_v2",
    )
    parser.add_argument(
        "--tracts_in",
        help="Comma-separated list of input DC2 tract numbers. Only (3828, 3829) are supported.",
        type=str,
        default="3828",
    )
    parser.add_argument(
        "--truth_summary_path",
        help="Path to DC2 truth_summary tables",
        type=str,
        default="/sdf/data/rubin/shared/dc2_run2.2i_truth/truth_summary_cell",
    )

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    tracts = tuple((int(tract) for tract in tracts.split(":", 1)) for tracts in args.tracts_out.split(","))

    bands = args.bands.split(",")
    butler_in = dafButler.Butler(args.butler_in)
    butler_out = dafButler.Butler(args.butler_out, collections=args.collection_out if args.plot else None)

    for tract_out, tract_in in tracts:
        catalogs, mags = convert_truth_summary_v2_to_injection(
            bands=bands,
            butler_in=butler_in,
            butler_out=butler_out,
            skymap_name_in=args.skymap_name_in,
            skymap_name_out=args.skymap_name_out,
            tract_in=tract_in,
            tract_out=tract_out,
            mag_total_min_star=args.mag_total_min_star,
            mag_total_min_galaxy=args.mag_total_min_galaxy,
            mag_total_max=args.mag_total_max,
            n_skip_extended=args.n_skip_extended,
            n_skip_psf=args.n_skip_psf,
            plot=args.plot,
            truth_summary_path=args.truth_summary_path,
        )

        for (filename, catalog), (band, mags_band) in zip(catalogs.items(), mags.items()):
            mag_column = catalog["mag"]
            desc = mag_column.description
            mag_column.description = f"{band}-band {desc}"
            mag_column[:] = mags_band
            pq.write_table(astropy_to_arrow(catalog), filename)
            mag_column.description = desc
