#include <doctest/doctest.h>

#include <cmath>
#include <string>

#include "nycsim/io/Json.h"

using namespace nycsim;
using namespace nycsim::json;

TEST_SUITE("io") {
  TEST_CASE("json parses documents, preserves order, finds nested values") {
    const char* text = R"({
      "schema_version": 1, "name": "KNYC", "temp_c": -3.5, "ok": true, "none": null,
      "arr": [1, 2.5, "x", [], {}], "nested": {"a": {"b": [10, 20]}},
      "esc": "quote\" backslash\\ slash\/ nl\n tab\t uni\u00e9 pair\ud83c\udf4e"
    })";
    auto r = parse(text);
    REQUIRE_MESSAGE(r.ok(), r.error().message, " at ", r.error().detail);
    const Value& v = *r;
    CHECK(v.isObject());
    CHECK(v.size() == 8);
    CHECK(v.find("schema_version")->asInt() == 1);
    CHECK(v.find("name")->asString() == "KNYC");
    CHECK(v.find("temp_c")->asNumber() == doctest::Approx(-3.5));
    CHECK(v.find("ok")->asBool());
    CHECK(v.find("none")->isNull());
    CHECK(v.find("arr")->size() == 5);
    CHECK(v.find("arr")->at(1)->asNumber() == doctest::Approx(2.5));
    CHECK(v.find("arr")->at(2)->asString() == "x");
    CHECK(v.find("arr")->at(3)->isArray());
    CHECK(v.find("arr")->at(4)->isObject());
    CHECK(v.find("arr")->at(5) == nullptr);
    CHECK(v.path({"nested", "a", "b"})->at(1)->asInt() == 20);
    CHECK(v.path({"nested", "zz"}) == nullptr);
    CHECK(v.find("missing") == nullptr);
    CHECK(v.find("esc")->asString() == std::string("quote\" backslash\\ slash/ nl\n tab\t uni\xC3\xA9 pair\xF0\x9F\x8D\x8E"));
    // Members in source order.
    CHECK(v.members()[0].key == "schema_version");
    CHECK(v.members()[7].key == "esc");
    // Fallbacks on type mismatch.
    CHECK(v.find("name")->asNumber(-1.0) == -1.0);
    CHECK(v.find("temp_c")->asString("d") == "d");
    CHECK(v.find("ok")->asInt(9) == 9);
  }

  TEST_CASE("json numbers are exact for typical values and follow the strict grammar") {
    CHECK(parseNumber("0").value() == 0.0);
    CHECK(parseNumber("-0").value() == 0.0);
    CHECK(std::signbit(parseNumber("-0").value()));
    CHECK(parseNumber("0.3").value() == 0.3);
    CHECK(parseNumber("1013.25").value() == 1013.25);
    CHECK(parseNumber("1e-7").value() == 1e-7);
    CHECK(parseNumber("1E+2").value() == 100.0);
    CHECK(parseNumber("2.5e3").value() == 2500.0);
    CHECK(parseNumber("9007199254740993").value() == 9007199254740992.0);  // rounds to even
    CHECK(parseNumber("123456789012345678901234567890").value() == doctest::Approx(1.2345678901234568e29));
    CHECK(parseNumber("0.000000000000000000000000001").value() == doctest::Approx(1e-27));
    CHECK(parseNumber("1e400").value() == INFINITY);
    CHECK(parseNumber("1e-400").value() == 0.0);
    CHECK(parseNumber("40.748440").value() == 40.748440);
    CHECK(parseNumber("-73.985664").value() == -73.985664);
    for (const char* bad : {"01", "1.", ".5", "+1", "1e", "1e+", "--1", "0x10", "NaN", "Infinity", "1 2", ""}) {
      CHECK_MESSAGE(!parseNumber(bad).ok(), bad);
    }
  }

  TEST_CASE("json rejects malformed input with byte offsets") {
    struct Case {
      const char* text;
      int64_t offset;
    };
    const Case cases[] = {
        {"", 0},          {"{", 1},           {"[1,]", 3},        {"{\"a\":1,}", 7},
        {"{a:1}", 1},     {"[1 2]", 3},       {"\"abc", 4},       {"tru", 0},
        {"[1]x", 3},      {"{\"a\" 1}", 5},   {"\"\\x\"", 2},     {"\"\\u12G4\"", 5},
        {"\"\\ud800\"", 7}, {"\"a\nb\"", 2},  {"01", 1},          {"// c\n1", 0},
        {"'a'", 0},       {"[NaN]", 1},
    };
    for (const Case& c : cases) {
      auto r = parse(c.text);
      REQUIRE_MESSAGE(!r.ok(), c.text);
      CHECK(r.error().code == ErrorCode::ParseError);
      CHECK_MESSAGE(r.error().detail == c.offset, c.text, " -> ", r.error().message, " at ", r.error().detail);
    }
    // Depth limit.
    std::string deep(300, '[');
    deep += std::string(300, ']');
    auto d = parse(deep);
    CHECK_FALSE(d.ok());
    std::string okDeep(100, '[');
    okDeep += std::string(100, ']');
    CHECK(parse(okDeep).ok());
  }

  TEST_CASE("json dump: compact, pretty, escaping, number formatting, round trip") {
    Value v = Value::object();
    v.set("a", 1);
    v.set("b", 2.5);
    v.set("c", "x\"y\\z\n\x01");
    v.set("d", Value::array());
    v.find("d")->push(true);
    v.find("d")->push(nullptr);
    v.find("d")->push(-0.1);
    v.set("e", Value::object());
    v.set("f", 1e21);
    v.set("g", 40.748440);
    v.set("h", std::nan(""));
    CHECK(dump(v) == R"({"a":1,"b":2.5,"c":"x\"y\\z\n\u0001","d":[true,null,-0.1],"e":{},"f":1e+21,"g":40.74844,"h":null})");
    const std::string pretty = dump(v, 2);
    CHECK(pretty.find("{\n  \"a\": 1,\n  \"b\": 2.5,") == 0);
    CHECK(pretty.find("\"d\": [\n    true,\n    null,\n    -0.1\n  ]") != std::string::npos);
    auto back = parse(pretty);
    REQUIRE(back.ok());
    CHECK(back->find("g")->asNumber() == 40.748440);
    CHECK(back->find("f")->asNumber() == 1e21);
    CHECK(back->find("h")->isNull());
    CHECK(dump(*back) == dump(v));
    // set replaces, erase removes, push converts null.
    v.set("a", 7);
    CHECK(v.find("a")->asInt() == 7);
    CHECK(v.size() == 8);
    CHECK(v.erase("a"));
    CHECK_FALSE(v.erase("a"));
    Value n;
    n.push(1);
    CHECK(n.isArray());
    Value o;
    o.set("k", "v");
    CHECK(o.isObject());
    CHECK(dump(Value(std::string_view("s"))) == "\"s\"");
    CHECK(dump(Value(int64_t(-9007199254740991))) == "-9007199254740991");
    CHECK(dump(Value(0.1 + 0.2)) == "0.30000000000000004");
    // Scalars at top level and whitespace.
    CHECK(parse(" \r\n\t 42 \n").value().asInt() == 42);
    CHECK(parse("\"s\"").value().asString() == "s");
    CHECK(parse("null").value().isNull());
  }
}
