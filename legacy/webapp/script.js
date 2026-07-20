var app = angular.module('App', ['ui.bootstrap', 'ngCookies']);

app.factory('ItemsService', ['$window', function($window) {
     var storageKey = 'items',
        _sessionStorage = $window.sessionStorage;
     return {
        // Returns stored items array if available or return default array
        getItems: function() {
            var itemsStr = _sessionStorage.getItem(storageKey);
            if(itemsStr) {
                return angular.fromJson(itemsStr);
            }         
            return ["http://o2.com", "http://o2.co.uk", "http://three.co.uk"]; // return default value when there is nothing stored in sessionStore                
        },
        // Adds the given item to the stored array and persists the array to sessionStorage
        putItem: function(item) {
            var itemsStr = _sessionStorage.getItem(storageKey),
            items = [];
            if(itemStr) {
                items = angular.fromJson(itemsStr);
            }

            items.push(item);
            _sessionStorage.setItem(storageKey, angular.toJson(items));
        }
     }
}]);

app.filter('startFrom', function () {
	return function (input, start) {
		if (input) {
			start = +start;
			return input.slice(start);
		}
		return [];
	};
});

app.controller('MainCtrl', ['$scope', 'filterFilter', function ($scope, filterFilter, ItemsService) {
	
	$scope.items = ["http://o2.com", "http://o2.co.uk", "http://three.co.uk", "name 4", "name 5", "name 6", "name 7", "name 8", "name 10", "custom", "custom 2"]; 
	//$scope.items = ItemsService.getItems();
	
	// cookies tests not working
	$scope.WriteCookie = function () {
        ItemsService.putItem($scope.items);
    };
	$scope.ReadCookie = function () {
    	$window.alert(ItemsService.getItems());
    };
	
	// add a new link if it is not in the list
	$scope.addLink = function () {
        $scope.errortext = "";
        if (!$scope.newItem) {return;}
        if ($scope.items.indexOf($scope.newItem) == -1) {
            $scope.items.push($scope.newItem);
			$scope.errortext = "Thank you for your submittion";
			$scope.resetFilters();
			ItemsService.putItem($scope.items); //not working cookies
        } else {
            $scope.errortext = "Link already in the list";
        }
    };
	
	// delete from list a new link if it is not in the list
	$scope.removeItem = function(item) {
    	$scope.items.splice($scope.items.indexOf(item), 1);
		$scope.resetFilters();
		$cookies.put('allItems', $scope.items)
  	};
	
	$scope.$watch(function() { return angular.toJson([$scope.items]); },
                function() {
					console.log('settings updated!'); 
				  	$scope.items = $scope.items;
                });
	
	// get the value at the given index
	$scope.getResult = function($index, x) {
    	$scope.indexResult = $scope.items[$index];
    	$scope.itemResult = x;
	};

	// create empty search model (object) to trigger $watch on update
	$scope.search = {};
	
	$scope.resetFilters = function () {
		// needs to be a function or it won't trigger a $watch
		$scope.search = {};
	};

	// pagination controls
	$scope.currentPage = 1;
	$scope.totalItems = $scope.items.length;
	$scope.entryLimit = 10; // items per page
	$scope.noOfPages = Math.ceil($scope.totalItems / $scope.entryLimit);

	// $watch search to update pagination
	$scope.$watch('search', function (Val) {
		$scope.filtered = filterFilter($scope.items, Val);
		$scope.totalItems = $scope.filtered.length;
		$scope.noOfPages = Math.ceil($scope.totalItems / $scope.entryLimit);
		$scope.currentPage = 1;
	}, true);
	
}]);