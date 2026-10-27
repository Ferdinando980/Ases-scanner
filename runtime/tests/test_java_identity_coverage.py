from ases.pipeline import scan_project


def test_python_protocol_dunders_are_not_hidden_by_private_name_rule(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'api.py').write_text(
        'class Protocol:\n'
        '    def __iter__(self):\n'
        '        return iter(())\n'
        '    def _helper(self):\n'
        '        return None\n', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    names = {row['name'] for row in model['recovered_requirements']}
    assert '__iter__' in names
    helper = next(row for row in model['recovered_requirements'] if row['name'] == '_helper')
    assert helper['entry_scope'] == 'implementation-local'
    assert helper['coverage']['max_call_depth'] == 0


def test_empty_public_void_method_has_no_fabricated_outcome_and_keeps_coverage(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'Api.java').write_text(
        'public class Api { public void close() { /* intentionally empty */ } }', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    api = next(row for row in model['api'] if row['name'] == 'close')
    assert api['body_present'] is True
    assert not any(row['name'] == 'close' for row in model['recovered_requirements'])
    assert any('Body is present, but no admitted return/error/effect evidence for close' in row['reason']
               for row in model['behavior_coverage'])


def test_nested_builder_owner_is_exact_and_mapping_is_unique(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'RandomStringGenerator.java').write_text(
        'package org.apache.commons.text;\n'
        'public class RandomStringGenerator {\n'
        '  public static class Builder {\n'
        '    public RandomStringGenerator build() { return get(); }\n'
        '    private RandomStringGenerator get() { return null; }\n'
        '  }\n'
        '}', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    builder = next(row for row in model['api'] if row['name'] == 'build')
    assert builder['qualified_name'] == 'org.apache.commons.text.RandomStringGenerator.Builder.build'
    assert builder['entity_ref']
    assert len([row for row in model['api'] if row['name'] == 'build']) == 1
    assert any(row['name'] == 'build' for row in model['recovered_requirements'])


def test_implicit_interface_default_and_enum_constant_methods_are_indexed(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'Api.java').write_text(
        'interface Api { int contract(); default int value() { return 7; } }\n'
        'enum Predicates { DIGITS { @Override public boolean test(int c) { return c > 0; } }; }',
        encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    api = {(row['name'], row['qualified_name']): row for row in model['api'] if row['kind'] == 'method'}
    default = next(row for (name, _), row in api.items() if name == 'value')
    enum_method = next(row for (name, _), row in api.items() if name == 'test')
    assert default['visibility'] == 'public' and default['entity_ref']
    contract = next(row for (name, _), row in api.items() if name == 'contract')
    assert contract['body_present'] is False
    assert enum_method['qualified_name'] == 'Predicates.DIGITS.test'
    assert enum_method['entity_ref']
    assert {'value', 'test'} <= {row['name'] for row in model['recovered_requirements']}
    assert any(row.get('reason') == 'excluded: declaration has no body' and row.get('entry') == 'Api.contract'
               for row in model['behavior_coverage'])


def test_dollar_named_java_type_keeps_method_and_behavior_identity(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / '$.java').write_text(
        'package io.vavr;\n'
        'public class $ {\n'
        '  public static int Tuple0() { return 0; }\n'
        '  @Deprecated // Keep the package-local declaration start stable.\n'
        '  static <T> String packageLocal(T value) { return "package-local"; }\n'
        '}\n', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    api = next(row for row in model['api'] if row['name'] == 'Tuple0')
    assert api['qualified_name'] == 'io.vavr.$.Tuple0'
    assert api['entity_ref']
    behavior = next(row for row in model['recovered_requirements'] if row['name'] == 'Tuple0')
    assert behavior['entry_points'] == [api['entity_ref']]
    assert behavior['external_outcomes'][0]['expression'] == '0'

    package_local = next(row for row in model['api'] if row['name'] == 'packageLocal')
    assert package_local['visibility'] == 'package-private'
    assert package_local['qualified_name'] == 'io.vavr.$.packageLocal'
    assert package_local['entity_ref']
    assert package_local['locations'][0]['line'] == 4
    package_behavior = next(row for row in model['recovered_requirements'] if row['name'] == 'packageLocal')
    assert package_behavior['entry_scope'] == 'package-local'
    assert package_behavior['entry_visibility'] == 'package-private'
    assert package_behavior['entry_points'] == [package_local['entity_ref']]
    assert [fact['expression'] for fact in package_behavior['returns']] == ['"package-local"']
    assert package_behavior['entity_refs'] == [package_local['entity_ref']]


def test_java_route_annotation_literals_survive_comment_masking(tmp_path):
    from ases.scanners.java import scan_java

    source = tmp_path / 'src'
    source.mkdir()
    (source / 'Api.java').write_text(
        'package example;\n'
        '@Controller\n'
        '@RequestMapping("/api")\n'
        'class Api {\n'
        '  @GetMapping("/users") // Keep route annotation strings intact.\n'
        '  public String users() { return "ok"; }\n'
        '}\n', encoding='utf-8')

    routes = [node for node in scan_java(source).nodes if node.kind == 'route']
    assert len(routes) == 1
    assert routes[0].name == 'GET /api/users'
    assert routes[0].metadata['path'] == '/api/users'
    assert routes[0].provenance.evidence == ['Api.java:5']


def test_java_annotated_method_binds_to_declaration_start_line(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'Api.java').write_text(
        'public class Api {\n'
        '  @Deprecated // Keep the annotation on the declaration identity.\n'
        '  public int value() { return 1; }\n'
        '}\n', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    api = next(row for row in model['api'] if row['name'] == 'value')
    behavior = next(row for row in model['recovered_requirements'] if row['name'] == 'value')
    assert api['locations'][0]['line'] == 2
    assert behavior['locations'][0]['line'] == 2
    assert behavior['locations'][0]['entity_ref'] == api['entity_ref']


def test_package_private_operation_keeps_internal_scope(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / '$.java').write_text('class $ { static int result() { return 42; } }', encoding='utf-8')
    model = scan_project(source, tmp_path / 'result.ases')['engineering_model']
    operation = next(row for row in model['operations'] if row['name'] == 'result')
    assert operation['entry_scope'] == 'package-local'
    assert operation['entry_visibility'] == 'package-private'
    assert operation['coverage']['method'] == 'explicit-entry-operations/4'
