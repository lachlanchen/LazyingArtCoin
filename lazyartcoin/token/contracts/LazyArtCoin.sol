// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/// @title LazyArtCoin (LAC)
/// @notice Credits token for the LazyArt platform; minting is controlled by the owner (recommended: multisig).
contract LazyArtCoin is ERC20, ERC20Burnable, ERC20Permit, Ownable, Pausable {
    /// @notice Normalized unit multiplier (10 ** decimals()).
    uint256 private constant DECIMALS_FACTOR = 10 ** 18;

    /// @notice Treasury wallet that receives freshly minted supply for platform operations.
    address public treasury;

    event TreasuryUpdated(address indexed previousTreasury, address indexed newTreasury);

    constructor(
        address initialOwner,
        address treasury_,
        uint256 initialSupply // whole tokens without decimals applied
    )
        ERC20("LazyArtCoin", "LAC")
        ERC20Permit("LazyArtCoin")
        Ownable(initialOwner)
    {
        require(initialOwner != address(0), "Owner cannot be zero");
        require(treasury_ != address(0), "Treasury cannot be zero");

        treasury = treasury_;

        if (initialSupply > 0) {
            _mint(treasury_, initialSupply * DECIMALS_FACTOR);
        }
    }

    /// @notice Owner-only mint that sends freshly minted tokens directly to the treasury wallet.
    /// @param wholeTokens Amount expressed in whole LAC (1 LAC = 10 ** 18 units).
    function mintToTreasury(uint256 wholeTokens) external onlyOwner {
        _mint(treasury, wholeTokens * DECIMALS_FACTOR);
    }

    /// @notice Owner-only mint that targets a specific account using whole tokens.
    /// @param account Recipient wallet address.
    /// @param wholeTokens Amount expressed in whole LAC (1 LAC = 10 ** 18 units).
    function mintTo(address account, uint256 wholeTokens) external onlyOwner {
        _mint(account, wholeTokens * DECIMALS_FACTOR);
    }

    /// @notice Owner-only mint that accepts already-scaled token units.
    /// @param account Recipient wallet address.
    /// @param rawAmount Amount including decimals (e.g., 1 ether for 1 LAC).
    function mintRaw(address account, uint256 rawAmount) external onlyOwner {
        _mint(account, rawAmount);
    }

    /// @notice Pause all token transfers. Recommended for emergency response only.
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice Resume token transfers after a pause.
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @notice Update the treasury address that receives newly minted supply.
    function setTreasury(address newTreasury) external onlyOwner {
        require(newTreasury != address(0), "Treasury cannot be zero");
        emit TreasuryUpdated(treasury, newTreasury);
        treasury = newTreasury;
    }

    function _update(address from, address to, uint256 value) internal override {
        require(!paused(), "Token transfers are paused");
        super._update(from, to, value);
    }
}
