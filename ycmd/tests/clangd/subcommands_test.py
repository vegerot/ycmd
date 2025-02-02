# encoding: utf-8
#
# Copyright (C) 2018 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest import ( assert_that,
                       contains,
                       contains_string,
                       equal_to,
                       has_entries,
                       has_entry,
                       matches_regexp )
from pprint import pprint
import requests
import os.path

from ycmd.tests.clangd import ( IsolatedYcmd,
                                SharedYcmd,
                                PathToTestFile,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    LineColMatcher,
                                    LocationMatcher,
                                    ErrorMatcher )
from ycmd.utils import ReadFile


# This test is isolated to trigger objcpp hooks, rather than fetching completer
# from cache.
@IsolatedYcmd()
def Subcommands_DefinedSubcommands_test( app ):
  file_path = PathToTestFile( 'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' )
  RunAfterInitialized( app, {
      'request': {
        'completer_target': 'filetype_default',
        'line_num': 10,
        'column_num': 3,
        'filetype': 'objcpp',
        'filepath': file_path
      },
      'expect': {
        'response': requests.codes.ok,
        'data': contains( *sorted( [ 'ExecuteCommand',
                                     'FixIt',
                                     'Format',
                                     'GetDoc',
                                     'GetDocImprecise',
                                     'GetType',
                                     'GetTypeImprecise',
                                     'GoTo',
                                     'GoToDeclaration',
                                     'GoToDefinition',
                                     'GoToImprecise',
                                     'GoToInclude',
                                     'GoToReferences',
                                     'RefactorRename',
                                     'RestartServer' ] ) )
      },
      'route': '/defined_subcommands',
  } )


@SharedYcmd
def Subcommands_GoTo_ZeroBasedLineAndColumn_test( app ):
  file_path = PathToTestFile( 'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' )
  RunAfterInitialized( app, {
      'request': {
          'contents': ReadFile( file_path ),
          'completer_target': 'filetype_default',
          'command_arguments': [ 'GoToDefinition' ],
          'line_num': 10,
          'column_num': 3,
          'filetype': 'cpp',
          'filepath': file_path
      },
      'expect': {
          'response': requests.codes.ok,
          'data': {
              'filepath': os.path.abspath( file_path ),
              'line_num': 2,
              'column_num': 8
          }
      },
      'route': '/run_completer_command',
  } )


@SharedYcmd
def RunGoToTest_all( app, folder, command, test ):
  filepath = PathToTestFile( folder, test[ 'req' ][ 0 ] )
  common_request = {
    'completer_target' : 'filetype_default',
    'filepath'         : filepath,
    'command_arguments': [ command ],
    'contents'         : ReadFile( filepath ),
    'filetype'         : 'cpp'
  }

  request = common_request
  request.update( {
    'line_num'  : test[ 'req' ][ 1 ],
    'column_num': test[ 'req' ][ 2 ],
  } )

  response = test[ 'res' ]

  if isinstance( response, list ):
    expect = {
      'response': requests.codes.ok,
      'data': contains( *[
        LocationMatcher(
          PathToTestFile( folder, os.path.normpath( location[ 0 ] ) ),
          location[ 1 ],
          location[ 2 ]
        ) for location in response
      ] )
    }
  elif isinstance( response, tuple ):
    expect = {
      'response': requests.codes.ok,
      'data': LocationMatcher(
        PathToTestFile( folder, os.path.normpath( response[ 0 ] ) ),
        response[ 1 ],
        response[ 2 ]
      )
    }
  else:
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, test[ 'res' ] )
    }

  RunAfterInitialized( app, {
    'request': request,
    'route'  : '/run_completer_command',
    'expect' : expect
  } )


def Subcommands_GoTo_all_test():
  tests = [
    # Local::x -> definition/declaration of x
    { 'req': ( 'goto.cc', 23, 21 ), 'res': ( 'goto.cc', 4, 9 ) },
    # Local::in_line -> definition/declaration of Local::in_line
    { 'req': ( 'goto.cc', 24, 26 ), 'res': ( 'goto.cc', 6, 10 ) },
    # Local -> definition/declaration of Local
    { 'req': ( 'goto.cc', 24, 16 ), 'res': ( 'goto.cc', 2, 11 ) },
    # Local::out_of_line -> definition of Local::out_of_line
    { 'req': ( 'goto.cc', 25, 27 ), 'res': ( 'goto.cc', 14, 13 ) },
    # GoToDeclaration alternates between definition and declaration
    { 'req': ( 'goto.cc', 14, 13 ), 'res': ( 'goto.cc', 11, 10 ) },
    { 'req': ( 'goto.cc', 11, 10 ), 'res': ( 'goto.cc', 14, 13 ) },
    # test -> definition and declaration of test
    { 'req': ( 'goto.cc', 21,  5 ), 'res': ( 'goto.cc', 19, 5 ) },
    { 'req': ( 'goto.cc', 19,  5 ), 'res': ( 'goto.cc', 21, 5 ) },
    # Unicøde
    { 'req': ( 'goto.cc', 34,  9 ), 'res': ( 'goto.cc', 32, 26 ) },
    # Another_Unicøde
    { 'req': ( 'goto.cc', 36, 17 ), 'res': ( 'goto.cc', 32, 54 ) },
    { 'req': ( 'goto.cc', 36, 25 ), 'res': ( 'goto.cc', 32, 54 ) },
    { 'req': ( 'goto.cc', 38,  3 ), 'res': ( 'goto.cc', 36, 28 ) },
    # Expected failures
    { 'req': ( 'goto.cc', 13,  1 ), 'res': 'Cannot jump to location' },
    { 'req': ( 'goto.cc', 16,  6 ), 'res': 'Cannot jump to location' },
  ]

  for test in tests:
    for cmd in [ 'GoToDefinition', 'GoTo', 'GoToImprecise' ]:
      yield RunGoToTest_all, '', cmd, test


def Subcommands_GoToDeclaration_all_test():
  tests = [
    # Local::x -> definition/declaration of x
    { 'req': ( 'goto.cc', 23, 21 ), 'res': ( 'goto.cc', 4, 9 ) },
    # Local::in_line -> definition/declaration of Local::in_line
    { 'req': ( 'goto.cc', 24, 26 ), 'res': ( 'goto.cc', 6, 10 ) },
    # Local -> definition/declaration of Local
    { 'req': ( 'goto.cc', 24, 16 ), 'res': ( 'goto.cc', 2, 11 ) },
    # Local::out_of_line -> declaration of Local::out_of_line
    { 'req': ( 'goto.cc', 25, 27 ), 'res': ( 'goto.cc', 11, 10 ) },
    # GoToDeclaration alternates between definition and declaration
    { 'req': ( 'goto.cc', 14, 13 ), 'res': ( 'goto.cc', 11, 10 ) },
    { 'req': ( 'goto.cc', 11, 10 ), 'res': ( 'goto.cc', 14, 13 ) },
    # test -> definition and declaration of test
    { 'req': ( 'goto.cc', 21,  5 ), 'res': ( 'goto.cc', 19, 5 ) },
    { 'req': ( 'goto.cc', 19,  5 ), 'res': ( 'goto.cc', 21, 5 ) },
    # Unicøde
    { 'req': ( 'goto.cc', 34,  9 ), 'res': ( 'goto.cc', 32, 26 ) },
    # Another_Unicøde
    { 'req': ( 'goto.cc', 36, 17 ), 'res': ( 'goto.cc', 32, 54 ) },
    { 'req': ( 'goto.cc', 36, 25 ), 'res': ( 'goto.cc', 32, 54 ) },
    { 'req': ( 'goto.cc', 38,  3 ), 'res': ( 'goto.cc', 36, 28 ) },
    # Expected failures
    { 'req': ( 'goto.cc', 13,  1 ), 'res': 'Cannot jump to location' },
    { 'req': ( 'goto.cc', 16,  6 ), 'res': 'Cannot jump to location' },
  ]

  for test in tests:
    yield RunGoToTest_all, '', 'GoToDeclaration', test


def Subcommands_GoToInclude_test():
  tests = [
    { 'req': ( 'main.cpp',  1,  6 ), 'res': ( 'a.hpp',        1, 1 ) },
    { 'req': ( 'main.cpp',  2, 14 ), 'res': ( 'system/a.hpp', 1, 1 ) },
    { 'req': ( 'main.cpp',  3,  1 ), 'res': ( 'quote/b.hpp',  1, 1 ) },
    # FIXME: should fail since b.hpp is included with angled brackets but its
    # folder is added with -iquote.
    { 'req': ( 'main.cpp',  4, 10 ), 'res': ( 'quote/b.hpp',  1, 1 ) },
    { 'req': ( 'main.cpp',  5, 11 ), 'res': ( 'system/c.hpp', 1, 1 ) },
    { 'req': ( 'main.cpp',  6, 11 ), 'res': ( 'system/c.hpp', 1, 1 ) },
    # Expected failures
    { 'req': ( 'main.cpp',  7,  1 ), 'res': 'Cannot jump to location' },
    { 'req': ( 'main.cpp', 10, 13 ), 'res': 'Cannot jump to location' },
  ]

  for test in tests:
    for cmd in [ 'GoToInclude', 'GoTo', 'GoToImprecise' ]:
      yield RunGoToTest_all, 'test-include', cmd, test


def Subcommands_GoToReferences_test():
  tests = [
    # Function
    { 'req': ( 'goto.cc', 14, 21 ), 'res': [ ( 'goto.cc', 11, 10 ),
                                             ( 'goto.cc', 14, 13 ),
                                             ( 'goto.cc', 25, 22 ) ] },
    # Namespace
    { 'req': ( 'goto.cc', 24, 17 ), 'res': [ ( 'goto.cc',  2, 11 ),
                                             ( 'goto.cc', 14,  6 ),
                                             ( 'goto.cc', 23, 14 ),
                                             ( 'goto.cc', 24, 15 ),
                                             ( 'goto.cc', 25, 15 ) ] },
    # Expected failure
    { 'req': ( 'goto.cc', 27,  8 ), 'res': 'Cannot jump to location' },
  ]

  for test in tests:
    yield RunGoToTest_all, '', 'GoToReferences', test


@SharedYcmd
def RunGetSemanticTest( app,
                        filepath,
                        filetype,
                        test,
                        command,
                        response = requests.codes.ok ):
  contents = ReadFile( filepath )
  common_args = {
    'completer_target' : 'filetype_default',
    'command_arguments': command,
    'line_num'         : 10,
    'column_num'       : 3,
    'filepath'         : filepath,
    'contents'         : contents,
    'filetype'         : filetype
  }

  args = test[ 0 ]
  if response == requests.codes.ok:
    if not isinstance( test[ 1 ], BaseMatcher ):
      expected = has_entry( 'message', contains_string( test[ 1 ] ) )
    else:
      expected = has_entry( 'message', test[ 1 ] )
  else:
    expected = test[ 1 ]

  request = common_args
  request.update( args )
  test = { 'request': request,
           'route': '/run_completer_command',
           'expect': { 'response': response,
                       'data': expected } }
  RunAfterInitialized( app, test )


def Subcommands_GetType_test():
  tests = [
    # Basic pod types
    [ { 'line_num': 24, 'column_num':  3 }, 'Foo' ],
    # [ { 'line_num': 12, 'column_num':  2 }, 'Foo' ],
    [ { 'line_num': 12, 'column_num':  8 }, 'Foo' ],
    [ { 'line_num': 12, 'column_num':  9 }, 'Foo' ],
    [ { 'line_num': 12, 'column_num': 10 }, 'Foo' ],
    # [ { 'line_num': 13, 'column_num':  3 }, 'int' ],
    [ { 'line_num': 13, 'column_num':  7 }, 'int' ],
    # [ { 'line_num': 15, 'column_num':  7 }, 'char' ],

    # Function
    # [ { 'line_num': 22, 'column_num':  2 }, 'int main()' ],
    [ { 'line_num': 22, 'column_num':  6 }, 'int main()' ],

    # Declared and canonical type
    # On Ns::
    [ { 'line_num': 25, 'column_num':  3 }, 'namespace Ns' ],
    # On Type (Type)
    # [ { 'line_num': 25, 'column_num':  8 },
    # 'Ns::Type => Ns::BasicType<char>' ],
    # On "a" (Ns::Type)
    # [ { 'line_num': 25, 'column_num': 15 },
    # 'Ns::Type => Ns::BasicType<char>' ],
    # [ { 'line_num': 26, 'column_num': 13 },
    # 'Ns::Type => Ns::BasicType<char>' ],

    # Cursor on decl for refs & pointers
    [ { 'line_num': 39, 'column_num':  3 }, 'Foo' ],
    [ { 'line_num': 39, 'column_num': 11 }, 'Foo &' ],
    [ { 'line_num': 39, 'column_num': 15 }, 'Foo' ],
    [ { 'line_num': 40, 'column_num':  3 }, 'Foo' ],
    [ { 'line_num': 40, 'column_num': 11 }, 'Foo *' ],
    [ { 'line_num': 40, 'column_num': 18 }, 'Foo' ],
    # [ { 'line_num': 42, 'column_num':  3 }, 'const Foo &' ],
    [ { 'line_num': 42, 'column_num': 16 }, 'const struct Foo &' ],
    # [ { 'line_num': 43, 'column_num':  3 }, 'const Foo *' ],
    [ { 'line_num': 43, 'column_num': 16 }, 'const struct Foo *' ],

    # Cursor on usage
    [ { 'line_num': 45, 'column_num': 13 }, 'const struct Foo' ],
    # [ { 'line_num': 45, 'column_num': 19 }, 'const int' ],
    [ { 'line_num': 46, 'column_num': 13 }, 'const struct Foo *' ],
    # [ { 'line_num': 46, 'column_num': 20 }, 'const int' ],
    [ { 'line_num': 47, 'column_num': 12 }, 'Foo' ],
    [ { 'line_num': 47, 'column_num': 17 }, 'int' ],
    [ { 'line_num': 48, 'column_num': 12 }, 'Foo *' ],
    [ { 'line_num': 48, 'column_num': 18 }, 'int' ],

    # Auto in declaration
    # [ { 'line_num': 28, 'column_num':  3 }, 'struct Foo &' ],
    # [ { 'line_num': 28, 'column_num': 11 }, 'struct Foo &' ],
    [ { 'line_num': 28, 'column_num': 18 }, 'struct Foo' ],
    # [ { 'line_num': 29, 'column_num':  3 }, 'Foo *' ],
    # [ { 'line_num': 29, 'column_num': 11 }, 'Foo *' ],
    [ { 'line_num': 29, 'column_num': 18 }, 'Foo' ],
    # [ { 'line_num': 31, 'column_num':  3 }, 'const Foo &' ],
    # [ { 'line_num': 31, 'column_num': 16 }, 'const Foo &' ],
    # [ { 'line_num': 32, 'column_num':  3 }, 'const Foo *' ],
    # [ { 'line_num': 32, 'column_num': 16 }, 'const Foo *' ],

    # Auto in usage
    # [ { 'line_num': 34, 'column_num': 14 }, 'const Foo' ],
    # [ { 'line_num': 34, 'column_num': 21 }, 'const int' ],
    # [ { 'line_num': 35, 'column_num': 14 }, 'const Foo *' ],
    # [ { 'line_num': 35, 'column_num': 22 }, 'const int' ],
    [ { 'line_num': 36, 'column_num': 13 }, 'Foo' ],
    [ { 'line_num': 36, 'column_num': 19 }, 'int' ],
    # [ { 'line_num': 37, 'column_num': 13 }, 'Foo *' ],
    [ { 'line_num': 37, 'column_num': 20 }, 'int' ],

    # Unicode
    [ { 'line_num': 51, 'column_num': 13 }, 'Unicøde *' ],

    # Bound methods
    # On Win32, methods pick up an __attribute__((thiscall)) to annotate their
    # calling convention.  This shows up in the type, which isn't ideal, but
    # also prohibitively complex to try and strip out.
    [ { 'line_num': 53, 'column_num': 15 },
      matches_regexp(
          r'int bar\(int i\)(?: __attribute__\(\(thiscall\)\))?' ) ],
    [ { 'line_num': 54, 'column_num': 18 },
      matches_regexp(
          r'int bar\(int i\)(?: __attribute__\(\(thiscall\)\))?' ) ],
  ]

  for subcommand in [ 'GetType', 'GetTypeImprecise' ]:
    for test in tests:
      yield ( RunGetSemanticTest,
              PathToTestFile( 'GetType_Clang_test.cc' ),
              'cpp',
              test,
              [ subcommand ] )


def Subcommands_GetDoc_test():
  tests = [
    # from local file
    [ { 'line_num': 5, 'column_num': 10 }, 'docstring', requests.codes.ok ],
    # from header
    [ { 'line_num': 6, 'column_num': 10 }, 'docstring', requests.codes.ok ],
    # no docstring
    [ { 'line_num': 7, 'column_num': 7 }, 'int x = 3', requests.codes.ok ],
    # no hover
    [ { 'line_num': 8, 'column_num': 1 },
      ErrorMatcher( RuntimeError, 'No hover information.' ),
      requests.codes.server_error ]
  ]
  for subcommand in [ 'GetDoc', 'GetDocImprecise' ]:
    for test in tests:
      yield ( RunGetSemanticTest,
              PathToTestFile( 'GetDoc_Clang_test.cc' ),
              'cpp',
              test,
              [ subcommand ],
              test[ 2 ] )


@SharedYcmd
def RunFixItTest( app, line, column, lang, file_path, check ):
  contents = ReadFile( file_path )

  language_options = {
    'cpp11': {
      'filetype'         : 'cpp',
    },
    'cuda': {
      'filetype'         : 'cuda',
    },
    'objective-c': {
      'filetype'         : 'objc',
    },
  }

  args = {
    'completer_target' : 'filetype_default',
    'contents'         : contents,
    'filepath'         : file_path,
    'command_arguments': [ 'FixIt' ],
    'line_num'         : line,
    'column_num'       : column,
  }
  args.update( language_options[ lang ] )
  test = { 'request': args, 'route': '/detailed_diagnostic' }
  # First get diags.
  diags = RunAfterInitialized( app, test )
  while 'message' in diags and 'diagnostics' in diags[ 'message' ].lower():
    receive_diags = { 'request': args, 'route': '/receive_messages' }
    RunAfterInitialized( app, receive_diags )
    diags = RunAfterInitialized( app, test )

  results = app.post_json( '/run_completer_command',
                           BuildRequest( **args ) ).json

  pprint( results )
  check( results )


def FixIt_Check_cpp11_Ins( results ):
  # First fixit
  #   switch(A()) { // expected-error{{explicit conversion to}}
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( 'static_cast<int>(' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 10 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 10 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to( ')' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 13 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 13 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 16, 'column_num': 0 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_InsMultiLine( results ):
  # Similar to FixIt_Check_cpp11_1 but inserts split across lines
  #
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( 'static_cast<int>(' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 26, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 26, 'column_num': 7 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to( ')' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 28, 'column_num': 2 } ),
            'end'  : has_entries( { 'line_num': 28, 'column_num': 2 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 25, 'column_num': 14 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Del( results ):
  # Removal of ::
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( '' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 35, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 35, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 35, 'column_num': 7 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Repl( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( 'foo' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 40, 'column_num': 6 } ),
            'end'  : has_entries( { 'line_num': 40, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 40, 'column_num': 6 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_DelAdd( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 48, 'column_num': 3 } ),
              'end'  : has_entries( { 'line_num': 48, 'column_num': 4 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to( '~' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 48, 'column_num': 9 } ),
              'end'  : has_entries( { 'line_num': 48, 'column_num': 9 } ),
            } ),
          } ),
        ),
        'location': has_entries( { 'line_num': 48, 'column_num': 3 } )
      } ),
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '= default;' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 48, 'column_num': 15 } ),
              'end'  : has_entries( { 'line_num': 48, 'column_num': 17 } ),
            } ),
          } ),
        ),
        'location': has_entries( { 'line_num': 48, 'column_num': 3 } )
      } ),
    )
  } ) )


def FixIt_Check_objc( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( 'id' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 5, 'column_num': 3 } ),
            'end'  : has_entries( { 'line_num': 5, 'column_num': 3 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 5, 'column_num': 3 } )
    } ) )
  } ) )


def FixIt_Check_objc_NoFixIt( results ):
  # and finally, a warning with no fixits
  assert_that( results, equal_to( { 'fixits': [] } ) )


def FixIt_Check_cpp11_MultiFirst( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # first fix-it at 54,16
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( 'foo' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 15 } )
      } ),
      # second fix-it at 54,52
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to( '~' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 58 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 58 } ),
            } ),
          } ),
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 15 } )
      } ),
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '= default;' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 64 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 67 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 15 } )
      } ),
    )
  } ) )


def FixIt_Check_cpp11_MultiSecond( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # first fix-it at 54,16
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( 'foo' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 51 } )
      } ),
      # second fix-it at 54,52
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to( '~' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 58 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 58 } ),
            } ),
          } ),
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 51 } )
      } ),
      has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to( '= default;' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 64 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 67 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 51 } )
      } ),
    )
  } ) )


def FixIt_Check_unicode_Ins( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries( {
      'chunks': contains(
        has_entries( {
          'replacement_text': equal_to( '=' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 21, 'column_num': 9 } ),
            'end'  : has_entries( { 'line_num': 21, 'column_num': 11 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 21, 'column_num': 16 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Note( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # First note: put parens around it
      has_entries( {
        'text': contains_string( 'parentheses around the assignment' ),
        'chunks': contains(
          ChunkMatcher( '(',
                        LineColMatcher( 59, 8 ),
                        LineColMatcher( 59, 8 ) ),
          ChunkMatcher( ')',
                        LineColMatcher( 61, 12 ),
                        LineColMatcher( 61, 12 ) )
        ),
        'location': LineColMatcher( 60, 1 ),
      } ),

      # Second note: change to ==
      has_entries( {
        'text': contains_string( '==' ),
        'chunks': contains(
          ChunkMatcher( '==',
                        LineColMatcher( 60, 8 ),
                        LineColMatcher( 60, 9 ) )
        ),
        'location': LineColMatcher( 60, 1 ),
      } )
    )
  } ) )


def FixIt_Check_cpp11_SpellCheck( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # Change to SpellingIsNotMyStrongPoint
      has_entries( {
        'text': contains_string( "change 'SpellingIsNotMyStringPiont' to "
                                 "'SpellingIsNotMyStrongPoint'" ),
        'chunks': contains(
          ChunkMatcher( 'SpellingIsNotMyStrongPoint',
                        LineColMatcher( 72, 9 ),
                        LineColMatcher( 72, 35 ) )
        ),
        'location': LineColMatcher( 72, 9 ),
      } ) )
  } ) )


def FixIt_Check_cuda( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      has_entries( {
        'text': contains_string(
           "change 'int' to 'void'" ),
        'chunks': contains(
          ChunkMatcher( 'void',
                        LineColMatcher( 3, 12 ),
                        LineColMatcher( 3, 15 ) )
        ),
        'location': LineColMatcher( 3, 12 ),
      } ) )
  } ) )


def Subcommands_FixIt_all_test():
  cfile = PathToTestFile( 'FixIt_Clang_cpp11.cpp' )
  mfile = PathToTestFile( 'objc', 'FixIt_Clang_objc.m' )
  cufile = PathToTestFile( 'cuda', 'fixit_test.cu' )
  ufile = PathToTestFile( 'unicode.cc' )

  tests = [
    # L
    # i   C
    # n   o
    # e   l   Lang     File,  Checker
    [ 16, 0,  'cpp11', cfile, FixIt_Check_cpp11_Ins ],
    [ 25, 14, 'cpp11', cfile, FixIt_Check_cpp11_InsMultiLine ],
    [ 35, 7,  'cpp11', cfile, FixIt_Check_cpp11_Del ],
    [ 40, 6,  'cpp11', cfile, FixIt_Check_cpp11_Repl ],
    [ 48, 3,  'cpp11', cfile, FixIt_Check_cpp11_DelAdd ],

    [ 5, 3,   'objective-c', mfile, FixIt_Check_objc ],
    [ 7, 1,   'objective-c', mfile, FixIt_Check_objc_NoFixIt ],

    [ 3, 12,  'cuda', cufile, FixIt_Check_cuda ],

    # multiple errors on a single line; both with fixits
    [ 54, 15, 'cpp11', cfile, FixIt_Check_cpp11_MultiFirst ],

    # should put closest fix-it first?
    [ 54, 51, 'cpp11', cfile, FixIt_Check_cpp11_MultiSecond ],

    # unicode in line for fixit
    [ 21, 16, 'cpp11', ufile, FixIt_Check_unicode_Ins ],

    # FixIt attached to a "child" diagnostic (i.e. a Note)
    [ 60, 1,  'cpp11', cfile, FixIt_Check_cpp11_Note ],

    # FixIt due to forced spell checking
    [ 72, 9,  'cpp11', cfile, FixIt_Check_cpp11_SpellCheck ],
  ]

  for test in tests:
    yield RunFixItTest, test[ 0 ], test[ 1 ], test[ 2 ], test[ 3 ], test[ 4 ]


@SharedYcmd
def Subcommands_RefactorRename_test( app ):
  test = {
    'request': {
      'filetype': 'cpp',
      'completer_target': 'filetype_default',
      'contents': ReadFile( PathToTestFile( 'basic.cpp' ) ),
      'filepath': PathToTestFile( 'basic.cpp' ),
      'command_arguments': [ 'RefactorRename', 'Bar' ],
      'line_num': 17,
      'column_num': 4,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( 'Bar',
                          LineColMatcher( 1, 8 ),
                          LineColMatcher( 1, 11 ) ),
            ChunkMatcher( 'Bar',
                          LineColMatcher( 9, 3 ),
                          LineColMatcher( 9, 6 ) ),
            ChunkMatcher( '\n\n',
                          LineColMatcher( 12, 2 ),
                          LineColMatcher( 15, 1 ) ),
            ChunkMatcher( 'Bar',
                          LineColMatcher( 15,  8 ),
                          LineColMatcher( 15, 11 ) ),
            ChunkMatcher( ' ',
                          LineColMatcher( 15,  46 ),
                          LineColMatcher( 16,  1 ) ),
            ChunkMatcher( 'Bar',
                          LineColMatcher( 17, 3 ),
                          LineColMatcher( 17, 6 ) ),
            ChunkMatcher( '',
                          LineColMatcher( 17, 14 ),
                          LineColMatcher( 17, 15 ) ),
            ChunkMatcher( ' ',
                          LineColMatcher( 17, 17 ),
                          LineColMatcher( 17, 17 ) ),
            ChunkMatcher( ' ',
                          LineColMatcher( 17, 19 ),
                          LineColMatcher( 17, 19 ) ),
          )
        } ) )
      } )
    },
    'route': '/run_completer_command'
  }
  RunAfterInitialized( app, test )
