#include<iostream>
#include<cmath>
#include<cstdio>
#include<string>
using namespace std;
int main(){
    freopen("submatrix.in","r",stdin);
    freopen("submatrix.out","w",stdout);
    short a,b;
    cin>>a>>b;
    int aa[259][51];
    for(int i=0;i<a;i++){
        for(int j=0;j<b;j++){
            cin>>aa[i][j];
        }
    }
    int max=-100000;
    int sum=0;
    for(int i=0;i<a;i++){
        for(int j=i;j<a;j++){
            for(int k=0;k<b;k++){
                for(int l=k;l<b;l++){
                    sum=0;
                    for(int p=i;p<=j;p++){
                        for(int q=k;q<=l;q++){
                            sum+=aa[p][q];
                        }
                    }
                    if(sum>max){
                        max=sum;
                    }
                }
            }
        }
    }
    cout<<max<<endl;
    return 0;

}