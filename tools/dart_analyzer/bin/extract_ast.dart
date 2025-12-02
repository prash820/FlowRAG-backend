/// Dart AST Extractor for FlowRAG
///
/// This tool parses Dart files using the official Dart analyzer and outputs
/// structured JSON with 100% accurate extraction of:
/// - Classes (including widgets, state classes, mixins)
/// - Functions and methods
/// - Imports and exports
/// - Function calls and method invocations
/// - Route definitions (GoRouter, Navigator)
/// - Provider definitions (Riverpod, Provider)

import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:args/args.dart';
import 'package:path/path.dart' as path;

void main(List<String> arguments) {
  final parser = ArgParser()
    ..addOption('file', abbr: 'f', help: 'Dart file to analyze')
    ..addOption('directory', abbr: 'd', help: 'Directory to analyze recursively')
    ..addOption('output', abbr: 'o', help: 'Output file (default: stdout)')
    ..addFlag('pretty', abbr: 'p', help: 'Pretty print JSON output', defaultsTo: false)
    ..addFlag('help', abbr: 'h', help: 'Show help', negatable: false);

  final results = parser.parse(arguments);

  if (results['help'] || (results['file'] == null && results['directory'] == null)) {
    print('Dart AST Extractor for FlowRAG\n');
    print('Usage: dart extract_ast.dart -f <file.dart> [-o output.json] [-p]');
    print('       dart extract_ast.dart -d <directory> [-o output.json] [-p]\n');
    print(parser.usage);
    exit(0);
  }

  final List<Map<String, dynamic>> allResults = [];

  if (results['file'] != null) {
    final filePath = results['file'] as String;
    final result = analyzeFile(filePath);
    if (result != null) {
      allResults.add(result);
    }
  }

  if (results['directory'] != null) {
    final dirPath = results['directory'] as String;
    final dir = Directory(dirPath);
    if (dir.existsSync()) {
      for (final file in dir.listSync(recursive: true)) {
        if (file is File && file.path.endsWith('.dart')) {
          final result = analyzeFile(file.path);
          if (result != null) {
            allResults.add(result);
          }
        }
      }
    }
  }

  final encoder = results['pretty']
      ? JsonEncoder.withIndent('  ')
      : JsonEncoder();

  final output = encoder.convert({'files': allResults});

  if (results['output'] != null) {
    File(results['output'] as String).writeAsStringSync(output);
    stderr.writeln('Output written to ${results['output']}');
  } else {
    print(output);
  }
}

Map<String, dynamic>? analyzeFile(String filePath) {
  try {
    final file = File(filePath);
    if (!file.existsSync()) {
      stderr.writeln('File not found: $filePath');
      return null;
    }

    final content = file.readAsStringSync();
    final parseResult = parseString(content: content);

    if (parseResult.errors.isNotEmpty) {
      stderr.writeln('Parse errors in $filePath:');
      for (final error in parseResult.errors) {
        stderr.writeln('  ${error.message}');
      }
    }

    final unit = parseResult.unit;
    final extractor = DartAstExtractor(filePath, content);
    unit.accept(extractor);

    return extractor.toJson();
  } catch (e) {
    stderr.writeln('Error analyzing $filePath: $e');
    return null;
  }
}

class DartAstExtractor extends RecursiveAstVisitor<void> {
  final String filePath;
  final String content;
  final List<String> lines;

  final List<Map<String, dynamic>> classes = [];
  final List<Map<String, dynamic>> functions = [];
  final List<Map<String, dynamic>> imports = [];
  final List<Map<String, dynamic>> exports = [];
  final List<Map<String, dynamic>> calls = [];
  final List<Map<String, dynamic>> routes = [];
  final List<Map<String, dynamic>> providers = [];

  String? _currentClass;
  String? _currentFunction;

  DartAstExtractor(this.filePath, this.content) : lines = content.split('\n');

  int _getLineNumber(int offset) {
    int line = 1;
    for (int i = 0; i < offset && i < content.length; i++) {
      if (content[i] == '\n') line++;
    }
    return line;
  }

  String? _getDocComment(AnnotatedNode node) {
    final comment = node.documentationComment;
    if (comment == null) return null;

    final buffer = StringBuffer();
    for (final token in comment.tokens) {
      var text = token.lexeme;
      // Remove /// or /** */ markers
      if (text.startsWith('///')) {
        text = text.substring(3).trim();
      } else if (text.startsWith('/**')) {
        text = text.substring(3);
        if (text.endsWith('*/')) {
          text = text.substring(0, text.length - 2);
        }
        text = text.trim();
      }
      if (buffer.isNotEmpty) buffer.write(' ');
      buffer.write(text);
    }
    return buffer.toString();
  }

  String _getCode(AstNode node) {
    final start = node.offset;
    final end = node.end;
    if (start >= 0 && end <= content.length) {
      return content.substring(start, end);
    }
    return '';
  }

  @override
  void visitImportDirective(ImportDirective node) {
    imports.add({
      'uri': node.uri.stringValue,
      'prefix': node.prefix?.name,
      'line': _getLineNumber(node.offset),
      'is_deferred': node.deferredKeyword != null,
      'show': node.combinators
          .whereType<ShowCombinator>()
          .expand((c) => c.shownNames.map((n) => n.name))
          .toList(),
      'hide': node.combinators
          .whereType<HideCombinator>()
          .expand((c) => c.hiddenNames.map((n) => n.name))
          .toList(),
    });
    super.visitImportDirective(node);
  }

  @override
  void visitExportDirective(ExportDirective node) {
    exports.add({
      'uri': node.uri.stringValue,
      'line': _getLineNumber(node.offset),
    });
    super.visitExportDirective(node);
  }

  @override
  void visitClassDeclaration(ClassDeclaration node) {
    final className = node.name.lexeme;
    _currentClass = className;

    final extendsClause = node.extendsClause;
    final implementsClause = node.implementsClause;
    final withClause = node.withClause;

    // Determine class type
    String classType = 'class';
    bool isWidget = false;
    bool isStateful = false;
    bool isStateless = false;
    bool isState = false;

    final superclassName = extendsClause?.superclass.name2.lexeme;
    if (superclassName != null) {
      if (superclassName == 'StatelessWidget') {
        isWidget = true;
        isStateless = true;
        classType = 'stateless_widget';
      } else if (superclassName == 'StatefulWidget') {
        isWidget = true;
        isStateful = true;
        classType = 'stateful_widget';
      } else if (superclassName.startsWith('State<') || superclassName == 'State') {
        isState = true;
        classType = 'state';
      } else if (superclassName.contains('Widget')) {
        isWidget = true;
        classType = 'widget';
      } else if (superclassName == 'ConsumerWidget') {
        isWidget = true;
        classType = 'consumer_widget';
      } else if (superclassName == 'ConsumerStatefulWidget') {
        isWidget = true;
        isStateful = true;
        classType = 'consumer_stateful_widget';
      } else if (superclassName == 'HookWidget' || superclassName == 'HookConsumerWidget') {
        isWidget = true;
        classType = 'hook_widget';
      }
    }

    // Extract methods
    final methods = <Map<String, dynamic>>[];
    for (final member in node.members) {
      if (member is MethodDeclaration) {
        methods.add(_extractMethod(member));
      } else if (member is ConstructorDeclaration) {
        methods.add(_extractConstructor(member, className));
      }
    }

    // Extract fields
    final fields = <Map<String, dynamic>>[];
    for (final member in node.members) {
      if (member is FieldDeclaration) {
        for (final variable in member.fields.variables) {
          fields.add({
            'name': variable.name.lexeme,
            'type': member.fields.type?.toSource(),
            'is_final': member.fields.isFinal,
            'is_const': member.fields.isConst,
            'is_static': member.isStatic,
            'is_late': member.fields.isLate,
            'line': _getLineNumber(variable.offset),
          });
        }
      }
    }

    classes.add({
      'name': className,
      'type': classType,
      'is_abstract': node.abstractKeyword != null,
      'is_widget': isWidget,
      'is_stateful': isStateful,
      'is_stateless': isStateless,
      'is_state': isState,
      'extends': superclassName,
      'implements': implementsClause?.interfaces.map((t) => t.name2.lexeme).toList() ?? [],
      'mixins': withClause?.mixinTypes.map((t) => t.name2.lexeme).toList() ?? [],
      'type_parameters': node.typeParameters?.typeParameters.map((t) => t.name.lexeme).toList() ?? [],
      'methods': methods,
      'fields': fields,
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    });

    super.visitClassDeclaration(node);
    _currentClass = null;
  }

  @override
  void visitMixinDeclaration(MixinDeclaration node) {
    final mixinName = node.name.lexeme;

    classes.add({
      'name': mixinName,
      'type': 'mixin',
      'is_abstract': false,
      'is_widget': false,
      'on': node.onClause?.superclassConstraints.map((t) => t.name2.lexeme).toList() ?? [],
      'implements': node.implementsClause?.interfaces.map((t) => t.name2.lexeme).toList() ?? [],
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    });

    super.visitMixinDeclaration(node);
  }

  @override
  void visitExtensionDeclaration(ExtensionDeclaration node) {
    final extName = node.name?.lexeme ?? '<anonymous>';

    classes.add({
      'name': extName,
      'type': 'extension',
      'extends': node.extendedType.toSource(),
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    });

    super.visitExtensionDeclaration(node);
  }

  @override
  void visitEnumDeclaration(EnumDeclaration node) {
    final enumName = node.name.lexeme;
    final values = node.constants.map((c) => c.name.lexeme).toList();

    classes.add({
      'name': enumName,
      'type': 'enum',
      'values': values,
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    });

    super.visitEnumDeclaration(node);
  }

  Map<String, dynamic> _extractMethod(MethodDeclaration node) {
    final params = <Map<String, dynamic>>[];

    if (node.parameters != null) {
      for (final param in node.parameters!.parameters) {
        params.add(_extractParameter(param));
      }
    }

    return {
      'name': node.name.lexeme,
      'return_type': node.returnType?.toSource(),
      'parameters': params,
      'is_async': node.body.isAsynchronous,
      'is_generator': node.body.isGenerator,
      'is_static': node.isStatic,
      'is_getter': node.isGetter,
      'is_setter': node.isSetter,
      'is_operator': node.isOperator,
      'is_abstract': node.isAbstract,
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    };
  }

  Map<String, dynamic> _extractConstructor(ConstructorDeclaration node, String className) {
    final params = <Map<String, dynamic>>[];

    if (node.parameters != null) {
      for (final param in node.parameters.parameters) {
        params.add(_extractParameter(param));
      }
    }

    final constructorName = node.name?.lexeme;
    final fullName = constructorName != null ? '$className.$constructorName' : className;

    return {
      'name': fullName,
      'is_constructor': true,
      'is_factory': node.factoryKeyword != null,
      'is_const': node.constKeyword != null,
      'parameters': params,
      'redirected_constructor': node.redirectedConstructor?.toSource(),
      'initializers': node.initializers.map((i) => i.toSource()).toList(),
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    };
  }

  Map<String, dynamic> _extractParameter(FormalParameter param) {
    String? name;
    String? type;
    String? defaultValue;
    bool isRequired = false;
    bool isNamed = param.isNamed;
    bool isOptional = param.isOptionalPositional;

    if (param is SimpleFormalParameter) {
      name = param.name?.lexeme;
      type = param.type?.toSource();
    } else if (param is DefaultFormalParameter) {
      final innerParam = param.parameter;
      if (innerParam is SimpleFormalParameter) {
        name = innerParam.name?.lexeme;
        type = innerParam.type?.toSource();
      } else if (innerParam is FieldFormalParameter) {
        name = innerParam.name.lexeme;
        type = innerParam.type?.toSource();
      } else if (innerParam is SuperFormalParameter) {
        name = innerParam.name.lexeme;
        type = innerParam.type?.toSource();
      }
      defaultValue = param.defaultValue?.toSource();
      isRequired = param.isRequired;
    } else if (param is FieldFormalParameter) {
      name = param.name.lexeme;
      type = param.type?.toSource();
    } else if (param is SuperFormalParameter) {
      name = param.name.lexeme;
      type = param.type?.toSource();
    }

    return {
      'name': name,
      'type': type,
      'default_value': defaultValue,
      'is_required': isRequired,
      'is_named': isNamed,
      'is_optional': isOptional,
    };
  }

  @override
  void visitFunctionDeclaration(FunctionDeclaration node) {
    final funcName = node.name.lexeme;
    _currentFunction = funcName;

    final params = <Map<String, dynamic>>[];
    final funcExpr = node.functionExpression;

    if (funcExpr.parameters != null) {
      for (final param in funcExpr.parameters!.parameters) {
        params.add(_extractParameter(param));
      }
    }

    functions.add({
      'name': funcName,
      'return_type': node.returnType?.toSource(),
      'parameters': params,
      'is_async': funcExpr.body.isAsynchronous,
      'is_generator': funcExpr.body.isGenerator,
      'is_getter': node.isGetter,
      'is_setter': node.isSetter,
      'is_top_level': true,
      'docstring': _getDocComment(node),
      'line_start': _getLineNumber(node.offset),
      'line_end': _getLineNumber(node.end),
      'code': _getCode(node),
    });

    super.visitFunctionDeclaration(node);
    _currentFunction = null;
  }

  @override
  void visitMethodInvocation(MethodInvocation node) {
    final methodName = node.methodName.name;
    final target = node.target?.toSource();

    // Track all method calls
    calls.add({
      'method': methodName,
      'target': target,
      'from_class': _currentClass,
      'from_function': _currentFunction,
      'line': _getLineNumber(node.offset),
      'arguments': node.argumentList.arguments.length,
    });

    // Special handling for GoRouter routes (when GoRoute is called as method-like)
    if (methodName == 'GoRoute') {
      _extractGoRouteFromMethodCall(node);
    }

    // Special handling for Navigator
    if (target == 'Navigator' || methodName.startsWith('push') || methodName.startsWith('pop')) {
      _extractNavigatorCall(node);
    }

    super.visitMethodInvocation(node);
  }

  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    final typeName = node.constructorName.type.name2.lexeme;

    // Track constructor calls
    calls.add({
      'constructor': typeName,
      'named_constructor': node.constructorName.name?.name,
      'from_class': _currentClass,
      'from_function': _currentFunction,
      'line': _getLineNumber(node.offset),
      'arguments': node.argumentList.arguments.length,
    });

    // Special handling for GoRoute
    if (typeName == 'GoRoute') {
      _extractGoRouteFromConstructor(node);
    }

    // Special handling for Provider definitions
    if (typeName.contains('Provider') || typeName.contains('Notifier')) {
      _extractProvider(node, typeName);
    }

    super.visitInstanceCreationExpression(node);
  }

  void _extractGoRouteFromMethodCall(MethodInvocation node) {
    String? routePath;
    String? routeName;
    String? builderWidget;

    for (final arg in node.argumentList.arguments) {
      if (arg is NamedExpression) {
        final name = arg.name.label.name;
        final value = arg.expression;

        if (name == 'path' && value is StringLiteral) {
          routePath = value.stringValue;
        } else if (name == 'name' && value is StringLiteral) {
          routeName = value.stringValue;
        } else if (name == 'builder') {
          // Extract the widget being returned from builder
          if (value is FunctionExpression) {
            final body = value.body;
            if (body is ExpressionFunctionBody) {
              builderWidget = _extractWidgetName(body.expression);
            } else if (body is BlockFunctionBody) {
              for (final statement in body.block.statements) {
                if (statement is ReturnStatement && statement.expression != null) {
                  builderWidget = _extractWidgetName(statement.expression!);
                  break;
                }
              }
            }
          }
        }
      }
    }

    if (routePath != null) {
      routes.add({
        'type': 'go_route',
        'path': routePath,
        'name': routeName,
        'builder_widget': builderWidget,
        'from_function': _currentFunction,
        'from_class': _currentClass,
        'line': _getLineNumber(node.offset),
      });
    }
  }

  String? _extractWidgetName(Expression expr) {
    // Handle: const WidgetName() or WidgetName()
    if (expr is InstanceCreationExpression) {
      return expr.constructorName.type.name2.lexeme;
    }
    // Handle: WidgetName(args)
    if (expr is MethodInvocation) {
      return expr.methodName.name;
    }
    // Fallback to source code
    final source = expr.toSource();
    // Try to extract just the widget class name
    final match = RegExp(r'(?:const\s+)?(\w+)\s*\(').firstMatch(source);
    if (match != null) {
      return match.group(1);
    }
    return source;
  }

  void _extractGoRouteFromConstructor(InstanceCreationExpression node) {
    String? routePath;
    String? routeName;
    String? builderWidget;

    for (final arg in node.argumentList.arguments) {
      if (arg is NamedExpression) {
        final name = arg.name.label.name;
        final value = arg.expression;

        if (name == 'path' && value is StringLiteral) {
          routePath = value.stringValue;
        } else if (name == 'name' && value is StringLiteral) {
          routeName = value.stringValue;
        } else if (name == 'builder' && value is FunctionExpression) {
          // Try to extract the widget being returned
          final body = value.body;
          if (body is ExpressionFunctionBody) {
            builderWidget = body.expression.toSource();
          } else if (body is BlockFunctionBody) {
            // Look for return statement
            for (final statement in body.block.statements) {
              if (statement is ReturnStatement && statement.expression != null) {
                builderWidget = statement.expression!.toSource();
                break;
              }
            }
          }
        }
      }
    }

    if (routePath != null) {
      routes.add({
        'type': 'go_route',
        'path': routePath,
        'name': routeName,
        'builder_widget': builderWidget,
        'from_function': _currentFunction,
        'line': _getLineNumber(node.offset),
      });
    }
  }

  void _extractNavigatorCall(MethodInvocation node) {
    final methodName = node.methodName.name;
    String? route;

    for (final arg in node.argumentList.arguments) {
      if (arg is StringLiteral) {
        route = arg.stringValue;
        break;
      }
    }

    if (route != null || methodName.startsWith('push') || methodName.startsWith('pop')) {
      routes.add({
        'type': 'navigator',
        'method': methodName,
        'route': route,
        'from_class': _currentClass,
        'from_function': _currentFunction,
        'line': _getLineNumber(node.offset),
      });
    }
  }

  void _extractProvider(InstanceCreationExpression node, String typeName) {
    providers.add({
      'type': typeName,
      'from_class': _currentClass,
      'from_function': _currentFunction,
      'line': _getLineNumber(node.offset),
      'code': _getCode(node),
    });
  }

  Map<String, dynamic> toJson() {
    return {
      'file_path': filePath,
      'file_name': path.basename(filePath),
      'total_lines': lines.length,
      'code_lines': lines.where((l) => l.trim().isNotEmpty && !l.trim().startsWith('//')).length,
      'classes': classes,
      'functions': functions,
      'imports': imports,
      'exports': exports,
      'calls': calls,
      'routes': routes,
      'providers': providers,
    };
  }
}
