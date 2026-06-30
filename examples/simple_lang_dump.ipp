#pragma once

#include <string_view>

namespace expressions {

namespace dump_detail {

inline void write_indent(std::ostream& out, int indent) {
    for (int index = 0; index < indent; ++index) {
        out.put(' ');
    }
}

inline void write_quoted(std::ostream& out, std::string_view value) {
    constexpr char hex[] = "0123456789abcdef";
    out.put('"');
    for (const unsigned char character : value) {
        switch (character) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (character < 0x20) {
                out << "\\u00" << hex[character >> 4] << hex[character & 0x0f];
            } else {
                out.put(static_cast<char>(character));
            }
        }
    }
    out.put('"');
}

}  // namespace dump_detail

template <class Context, class Value>
inline void dump_value(std::ostream& out, Context&, const Value& value) {
    out << value;
}

template <class Context>
inline void dump_value(std::ostream& out, Context&, const std::string& value) {
    dump_detail::write_quoted(out, value);
}

template <class Context>
inline void dump_value(std::ostream& out, Context&, bool value) {
    out << (value ? "true" : "false");
}

template <class Context>
inline void dump_value(std::ostream& out, Context&, op_t value) {
    switch (value) {
    case op_t::Add: out << "Add"; return;
    case op_t::Subtract: out << "Subtract"; return;
    case op_t::Multiply: out << "Multiply"; return;
    case op_t::Divide: out << "Divide"; return;
    case op_t::Modulus: out << "Modulus"; return;
    }
    out << "<unknown Op>";
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const op_t& value, int indent) {
    dump_detail::write_indent(out, indent);
    dump_value(out, ctx, value);
    out.put('\n');
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const expr& value, int indent) {
    std::visit(
        [&](const auto& alternative) { dump(out, ctx, alternative, indent); },
        value);
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const variable& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: Variable\n";
    dump_detail::write_indent(out, indent);
    out << "name:";
    out.put(' ');
    dump_value(out, ctx, value.name);
    out.put('\n');
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const number& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: Number\n";
    dump_detail::write_indent(out, indent);
    out << "value:";
    out.put(' ');
    dump_value(out, ctx, value.value);
    out.put('\n');
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const binary_expression& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: BinaryExpression\n";
    dump_detail::write_indent(out, indent);
    out << "op:";
    out.put(' ');
    dump_value(out, ctx, value.op);
    out.put('\n');
    dump_detail::write_indent(out, indent);
    out << "left:";
    if (!value.left) {
        out << " null\n";
    } else {
        out.put('\n');
        dump(out, ctx, *value.left, indent + 4);
    }
    dump_detail::write_indent(out, indent);
    out << "right:";
    if (!value.right) {
        out << " null\n";
    } else {
        out.put('\n');
        dump(out, ctx, *value.right, indent + 4);
    }
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const function_signature& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: FunctionSignature\n";
    dump_detail::write_indent(out, indent);
    out << "return_type:";
    out.put(' ');
    dump_value(out, ctx, value.return_type);
    out.put('\n');
    dump_detail::write_indent(out, indent);
    out << "parameter_types:";
    if (value.parameter_types.empty()) {
        out << " []\n";
    } else {
        out.put('\n');
        for (const auto& item : value.parameter_types) {
            dump_detail::write_indent(out, indent + 4);
            out.put('-');
            out.put(' ');
            dump_value(out, ctx, item);
            out.put('\n');
        }
    }
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const function_head& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: FunctionHead\n";
    dump_detail::write_indent(out, indent);
    out << "name:";
    out.put(' ');
    dump_value(out, ctx, value.name);
    out.put('\n');
    dump_detail::write_indent(out, indent);
    out << "signature:";
    out.put('\n');
    dump(out, ctx, value.signature, indent + 4);
}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const function_definition& value, int indent) {
    dump_detail::write_indent(out, indent);
    out << "_type: FunctionDefinition\n";
    dump_detail::write_indent(out, indent);
    out << "head:";
    out.put('\n');
    dump(out, ctx, value.head, indent + 4);
    dump_detail::write_indent(out, indent);
    out << "code:";
    if (value.code.empty()) {
        out << " []\n";
    } else {
        out.put('\n');
        for (const auto& item : value.code) {
            dump_detail::write_indent(out, indent + 4);
            out.put('-');
            if (!item) {
                out << " null\n";
            } else {
                out.put('\n');
                dump(out, ctx, *item, indent + 8);
            }
        }
    }
}

}  // namespace expressions
