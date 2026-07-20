// Code goes here

var app = angular.module("CartApp",['ngCookies']);

app.controller("CartForm",function($scope,$cookieStore) {
    $scope.invoice = {
        items: [{
            qty: 10,
            description: 'item',
            cost: 9.95}]
    };

    $scope.addItem = function() {
        $scope.invoice.items.push({
            qty: 1,
            description: '',
            cost: 0
        });
    };

    $scope.removeItem = function(index) {
        $scope.invoice.items.splice(index, 1);
    };

$scope.storeProductsInCookie=function(){
  $cookieStore.put("invoices",$scope.invoice.items)
  
};

$scope.getProductsInCookie=function(){
 console.log(  $cookieStore.get("invoices",$scope.invoices));
  
};

    $scope.total = function() {
        var total = 0;
        angular.forEach($scope.invoice.items, function(item) {
            total += item.qty * item.cost;
        })

        return total;
    }
});