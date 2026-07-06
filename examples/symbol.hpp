#pragma once

#include <cstddef>
#include <ostream>

struct type_id {
    std::size_t index;
};

struct symbol_id {
    std::size_t index;
};

struct source_position {
    std::string filename = "";
    size_t line = 1;
    size_t column = 1;
};

struct source_range {
    source_position start;
    source_position end;
};

struct function_parameter
{
    std::string name;
};

struct function_signature
{
    std::vector<function_parameter> parameters;
    type_id function_type;
};

inline std::ostream& operator<<(std::ostream& out, const source_range& value) {
    return out << value.start.line << ".." << value.end.line;
}
