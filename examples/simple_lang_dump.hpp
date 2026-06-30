#pragma once

#include "simple_lang.hpp"

#include <ostream>
#include <string>

namespace expressions {

template <class Context, class Value>
void dump_value(std::ostream& out, Context& ctx, const Value& value);

template <class Context>
void dump_value(std::ostream& out, Context& ctx, const std::string& value);

template <class Context>
void dump_value(std::ostream& out, Context& ctx, bool value);

template <class Context>
void dump(std::ostream& out, Context& ctx, const op_t& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const expr& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const variable& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const number& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const binary_expression& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const function_signature& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const function_head& value, int indent = 0);

template <class Context>
void dump(std::ostream& out, Context& ctx, const function_definition& value, int indent = 0);

}  // namespace expressions

#include "simple_lang_dump.ipp"
