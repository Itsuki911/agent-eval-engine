$actual = & ./Greet.ps1 -Name agent
if ($actual -ne "hello agent") {
  throw "期待値と異なります: $actual"
}
