from tree_sitter import Language

Language.build_library(
    # Path to build the shared library
    'build/my-languages.so',

    # Languages to include
    [
        './tree-sitter-cpp'
    ]
)
