// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Counter {
    uint256 public x;

    event Increment(uint256 by);

    function inc() external {
        x += 1;
        emit Increment(1);
    }

    function incBy(uint256 by) external {
        x += by;
        emit Increment(by);
    }
}